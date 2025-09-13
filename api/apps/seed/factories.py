"""
Factory-boy factories for generating realistic ESG-focused synthetic data.
"""

import factory
import random
from datetime import date, timedelta
from typing import List, Dict, Any

from apps.skills.models import Skill
from apps.organisations.models import Organisation
from apps.profiles.models import Profile, ProfileExperience, ProfileSkill, ProfileExperienceSkill
from apps.opportunities.models import Opportunity, OpportunitySkill, OpportunityExperience

from .esg_definitions import (
    ESG_SKILLS, ESG_INDUSTRIES, ESG_PERSONAS, CAREER_PROGRESSION,
    get_skills_for_year
)
from .esg_content_generator import ESGContentGenerator


class SkillFactory(factory.django.DjangoModelFactory):
    """Factory for creating ESG skills"""
    
    class Meta:
        model = Skill
        django_get_or_create = ('name',)  # Don't create duplicates
    
    name = factory.Iterator([
        skill for category in ESG_SKILLS.values() 
        for skill in category
    ])


class OrganisationFactory(factory.django.DjangoModelFactory):
    """Factory for creating ESG-focused organizations"""
    
    class Meta:
        model = Organisation
        django_get_or_create = ('name',)
    
    name = factory.Iterator([
        company for industry_data in ESG_INDUSTRIES.values()
        for company in industry_data['companies']
    ])


class ProfileFactory(factory.django.DjangoModelFactory):
    """Factory for creating realistic ESG professional profiles"""
    
    class Meta:
        model = Profile
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttribute(
        lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@email.com"
    )


class ESGProfileBuilder:
    """
    Sophisticated builder for creating complete ESG career profiles.
    Uses persona-driven generation with realistic career progression.
    """
    
    def __init__(self):
        self.content_generator = ESGContentGenerator()
    
    def build_esg_profile(self, persona_name: str) -> Profile:
        """
        Build a complete ESG profile with realistic career progression.
        
        Args:
            persona_name: Key from ESG_PERSONAS
            
        Returns:
            Profile with experiences, skills, and experience-skills
        """
        persona = ESG_PERSONAS[persona_name]
        
        # Create base profile
        profile = ProfileFactory()
        
        # Generate career timeline
        career_timeline = self._generate_career_timeline(persona)
        
        # Create experiences with realistic progression
        experiences = []
        for exp_data in career_timeline:
            experience = self._create_experience(profile, exp_data)
            experiences.append(experience)
        
        # Create profile-level skills (aggregated from experiences)
        self._create_profile_skills(profile, experiences, persona)
        
        # Create experience-skill relationships
        for experience in experiences:
            self._create_experience_skills(experience)
        
        return profile
    
    def _generate_career_timeline(self, persona: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate realistic career progression for persona"""
        timeline = []
        
        min_years, max_years = persona['experience_range']
        total_years = random.randint(min_years, max_years)
        
        # Calculate current date and work backwards
        current_date = date.today()
        end_date = current_date
        
        # Generate 2-4 roles based on total experience
        num_roles = min(4, max(2, total_years // 2))
        years_per_role = total_years / num_roles
        
        # Choose industry progression (usually within same domain)
        industry_progression = self._choose_industry_progression(persona)
        
        for i in range(num_roles):
            # Calculate role duration
            role_years = max(1, int(years_per_role + random.uniform(-0.5, 0.5)))
            start_date = end_date - timedelta(days=role_years * 365)
            
            # Determine seniority based on position in career
            career_progress = i / (num_roles - 1) if num_roles > 1 else 0
            seniority = self._determine_seniority(total_years, career_progress)
            
            # Choose title based on seniority and persona
            title = self._choose_title(persona, seniority, i)
            
            # Choose company and industry
            industry = industry_progression[min(i, len(industry_progression) - 1)]
            company = random.choice(ESG_INDUSTRIES[industry]['companies'])
            
            # Choose skills for this role (based on year and progression)
            role_skills = self._choose_role_skills(persona, seniority, start_date.year)
            
            timeline.append({
                'title': title,
                'company': company,
                'industry': industry,
                'start_date': start_date,
                'end_date': end_date if i > 0 else None,  # Current role has no end date
                'duration_months': role_years * 12,
                'seniority': seniority,
                'skills': role_skills
            })
            
            end_date = start_date
        
        return list(reversed(timeline))  # Chronological order
    
    def _choose_industry_progression(self, persona: Dict[str, Any]) -> List[str]:
        """Choose realistic industry progression for persona"""
        available_industries = persona['industries']
        
        # Most people stay in same industry, some transition
        if random.random() < 0.7:  # 70% stay in same industry
            chosen_industry = random.choice(available_industries)
            return [chosen_industry] * 4  # Same industry for all roles
        else:  # 30% transition between related industries
            return random.sample(available_industries, min(2, len(available_industries))) * 2
    
    def _determine_seniority(self, total_years: int, career_progress: float) -> str:
        """Determine seniority level based on experience and career progress"""
        if total_years <= 2:
            return 'entry'
        elif total_years <= 5:
            return 'mid' if career_progress > 0.5 else 'entry'
        elif total_years <= 8:
            return 'senior' if career_progress > 0.6 else 'mid'
        else:
            return 'executive' if career_progress > 0.7 else 'senior'
    
    def _choose_title(self, persona: Dict[str, Any], seniority: str, role_index: int) -> str:
        """Choose appropriate title based on persona and seniority"""
        title_progression = persona['title_progression']
        
        if seniority == 'entry':
            return title_progression[0]
        elif seniority == 'mid':
            return title_progression[min(1, len(title_progression) - 1)]
        elif seniority == 'senior':
            return title_progression[min(2, len(title_progression) - 1)]
        else:  # executive
            return title_progression[-1]
    
    def _choose_role_skills(self, persona: Dict[str, Any], seniority: str, year: int) -> List[str]:
        """Choose appropriate skills for role based on seniority and year"""
        # Get skills available in that year
        available_skills = get_skills_for_year(year)
        
        # Build skill pool based on persona and seniority
        skill_pool = persona['core_skills'].copy()
        
        if seniority in ['mid', 'senior', 'executive']:
            skill_pool.extend(persona['progression_skills'])
        
        if seniority in ['senior', 'executive']:
            skill_pool.extend(persona['advanced_skills'])
        
        # Filter by year availability and remove duplicates
        available_skill_pool = list(set([
            skill for skill in skill_pool 
            if any(avail_skill in skill for avail_skill in available_skills)
        ]))
        
        # If no skills match year criteria, use core skills
        if not available_skill_pool:
            available_skill_pool = persona['core_skills'][:3]  # Fallback to first 3 core skills
        
        # Return 3-6 skills for the role (but don't exceed available skills)
        max_skills = min(6, len(available_skill_pool))
        if max_skills == 0:
            return []
        
        num_skills = random.randint(1, max_skills)
        return random.sample(available_skill_pool, num_skills)
    
    def _create_experience(self, profile: Profile, exp_data: Dict[str, Any]) -> ProfileExperience:
        """Create realistic experience with LLM-generated description"""
        
        # Get or create organization
        organisation, _ = Organisation.objects.get_or_create(name=exp_data['company'])
        
        # Generate realistic description using LLM
        description = self.content_generator.generate_experience_description({
            'title': exp_data['title'],
            'company': exp_data['company'],
            'industry': exp_data['industry'],
            'duration_months': exp_data['duration_months'],
            'skills': exp_data['skills'],
            'seniority': exp_data['seniority']
        })
        
        experience = ProfileExperience.objects.create(
            profile=profile,
            organisation=organisation,
            title=exp_data['title'],
            description=description,
            start_date=exp_data['start_date'],
            end_date=exp_data['end_date']
        )
        
        # Store skills data for later use
        experience._skills_data = exp_data['skills']
        
        return experience
    
    def _create_profile_skills(self, profile: Profile, experiences: List[ProfileExperience], persona: Dict[str, Any]):
        """Create profile-level skills based on experiences"""
        all_skills = set()
        
        # Collect all skills from experiences
        for exp in experiences:
            if hasattr(exp, '_skills_data'):
                all_skills.update(exp._skills_data)
        
        # Create ProfileSkill records with evidence levels
        evidence_weights = persona['evidence_weights']
        
        for skill_name in all_skills:
            skill, _ = Skill.objects.get_or_create(name=skill_name)
            
            # Determine evidence level based on persona weights
            evidence_level = random.choices(
                list(evidence_weights.keys()),
                weights=list(evidence_weights.values())
            )[0]
            
            ProfileSkill.objects.create(
                profile=profile,
                skill=skill,
                evidence_level=evidence_level
            )
    
    def _create_experience_skills(self, experience: ProfileExperience):
        """Create experience-skill relationships"""
        if hasattr(experience, '_skills_data'):
            for skill_name in experience._skills_data:
                skill, _ = Skill.objects.get_or_create(name=skill_name)
                ProfileExperienceSkill.objects.create(
                    profile_experience=experience,
                    skill=skill
                )


class OpportunityFactory(factory.django.DjangoModelFactory):
    """Factory for creating ESG opportunities"""
    
    class Meta:
        model = Opportunity
    
    @factory.lazy_attribute
    def organisation(self):
        # Choose random ESG organization
        return random.choice(Organisation.objects.all())
    
    title = factory.Iterator([
        role for industry_data in ESG_INDUSTRIES.values()
        for role in industry_data['typical_roles']
    ])
    
    @factory.lazy_attribute
    def description(self):
        # This will be enhanced with LLM generation
        return f"Join our team as {self.title} to drive ESG initiatives and sustainability strategy."


class ESGOpportunityBuilder:
    """Builder for creating realistic ESG opportunities with LLM-generated content"""
    
    def __init__(self):
        self.content_generator = ESGContentGenerator()
    
    def build_esg_opportunity(self, industry: str, seniority: str = None) -> Opportunity:
        """Build realistic ESG opportunity for specific industry"""
        
        industry_data = ESG_INDUSTRIES[industry]
        
        # Choose role and company
        role = random.choice(industry_data['typical_roles'])
        company = random.choice(industry_data['companies'])
        
        # Determine seniority if not provided
        if not seniority:
            seniority = random.choice(['entry', 'mid', 'senior'])
        
        # Choose required and preferred skills
        focus_areas = industry_data['focus_areas']
        required_skills = self._choose_opportunity_skills(focus_areas, 'required', 3, 5)
        preferred_skills = self._choose_opportunity_skills(focus_areas, 'preferred', 2, 4)
        
        # Get or create organization
        organisation, _ = Organisation.objects.get_or_create(name=company)
        
        # Generate realistic job description
        description = self.content_generator.generate_job_description({
            'title': role,
            'company': company,
            'industry': industry,
            'required_skills': required_skills,
            'preferred_skills': preferred_skills,
            'seniority': seniority
        })
        
        # Create opportunity
        opportunity = Opportunity.objects.create(
            organisation=organisation,
            title=role,
            description=description
        )
        
        # Create opportunity skills
        self._create_opportunity_skills(opportunity, required_skills, 'required')
        self._create_opportunity_skills(opportunity, preferred_skills, 'preferred')
        
        # Create opportunity experience requirements
        self._create_opportunity_experience(opportunity, industry, seniority, focus_areas)
        
        return opportunity
    
    def _choose_opportunity_skills(self, focus_areas: List[str], requirement_type: str, min_skills: int, max_skills: int) -> List[str]:
        """Choose appropriate skills for opportunity"""
        # This is simplified - in reality would use more sophisticated matching
        all_esg_skills = [skill for category in ESG_SKILLS.values() for skill in category]
        num_skills = random.randint(min_skills, max_skills)
        return random.sample(all_esg_skills, num_skills)
    
    def _create_opportunity_skills(self, opportunity: Opportunity, skills: List[str], requirement_type: str):
        """Create OpportunitySkill records"""
        for skill_name in skills:
            skill, _ = Skill.objects.get_or_create(name=skill_name)
            # Use get_or_create to avoid duplicates
            OpportunitySkill.objects.get_or_create(
                opportunity=opportunity,
                skill=skill,
                defaults={'requirement_type': requirement_type}
            )
    
    def _create_opportunity_experience(self, opportunity: Opportunity, industry: str, seniority: str, focus_areas: List[str]):
        """Create experience requirements for opportunity"""
        
        # Generate specific experience requirement
        description = self.content_generator.generate_opportunity_experience_requirement({
            'role_focus': focus_areas[0].lower().replace(' ', '_'),
            'industry': industry,
            'seniority': seniority,
            'specific_frameworks': random.sample(['TCFD', 'GRI', 'SASB', 'EU Taxonomy'], 2)
        })
        
        OpportunityExperience.objects.create(
            opportunity=opportunity,
            description=description
        )