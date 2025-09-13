"""
Comprehensive demonstration of the ESG Talent Matching System.
Shows complete data, embeddings, temporal weighting, and matching capabilities.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.profiles.models import Profile, ProfileExperience, ProfileSkill, ProfileExperienceSkill
from apps.opportunities.models import Opportunity, OpportunitySkill, OpportunityExperience
from apps.organisations.models import Organisation
from apps.skills.models import Skill
from apps.evaluations.models import EvaluationSet, Evaluation


class Command(BaseCommand):
    help = 'Show complete ESG talent matching system capabilities and data'

    def handle(self, *args, **options):
        self.stdout.write('🌱 ESG TALENT MATCHING SYSTEM - COMPLETE DEMONSTRATION')
        self.stdout.write('=' * 80)
        
        self._show_database_overview()
        self._show_sample_profiles()
        self._show_sample_opportunities()
        self._show_opportunity_matches()
        self._show_profile_matches()
        self._show_all_organizations()
        self._show_all_skills()
        self._show_embedding_examples()
        self._show_temporal_weighting()
        self._show_llm_reasoning_examples()
        self._show_system_capabilities()

    def _show_database_overview(self):
        self.stdout.write('\n📊 DATABASE OVERVIEW')
        self.stdout.write('-' * 40)
        
        # Count all major entities
        profile_count = Profile.objects.count()
        org_count = Organisation.objects.count()
        opp_count = Opportunity.objects.count()
        skill_count = Skill.objects.count()
        exp_count = ProfileExperience.objects.count()
        exp_skill_count = ProfileExperienceSkill.objects.count()
        eval_count = Evaluation.objects.count()
        llm_judged_count = Evaluation.objects.filter(was_llm_judged=True).count()
        
        self.stdout.write(f'👥 Profiles: {profile_count}')
        self.stdout.write(f'🏢 Organisations: {org_count}')
        self.stdout.write(f'🎯 Opportunities: {opp_count}')
        self.stdout.write(f'💡 Skills: {skill_count}')
        self.stdout.write(f'📋 Profile Experiences: {exp_count}')
        self.stdout.write(f'🔗 Profile-Experience-Skills: {exp_skill_count}')
        self.stdout.write(f'📈 Evaluations Run: {eval_count}')
        self.stdout.write(f'🧠 LLM Judgments: {llm_judged_count}')
        
        self.stdout.write('')
        self.stdout.write('📋 SCORE INTERPRETATION GUIDE')
        self.stdout.write('-' * 40)
        self.stdout.write('🔥 0.9-1.0: Exceptional match - immediate hire/pursue')
        self.stdout.write('⭐ 0.7-0.9: Strong match - proceed to interview')
        self.stdout.write('✅ 0.5-0.7: Good potential - worth considering')
        self.stdout.write('⚠️ 0.3-0.5: Moderate fit - some alignment, gaps exist')
        self.stdout.write('❌ 0.0-0.3: Weak match - poor fit')
        self.stdout.write('')
        self.stdout.write('📊 Score Components:')
        self.stdout.write('   • Structured: Skills overlap analysis (60% weight)')
        self.stdout.write('   • Semantic: Vector similarity matching (40% weight)')
        self.stdout.write('   • LLM Judge: Detailed reasoning for top 20% candidates')
        


    def _show_sample_profiles(self):
        self.stdout.write('\n\n👥 ALL PROFILES (Complete Career Journeys)')
        self.stdout.write('-' * 60)
        
        # Show ALL profiles in detail
        profiles = Profile.objects.all()
        
        for i, profile in enumerate(profiles, 1):
            self.stdout.write(f'\n{i}. 🧑 {profile.first_name} {profile.last_name}')
            self.stdout.write(f'   📧 {profile.email}')
            
            # Career progression (most recent first)
            experiences = profile.profile_experiences.order_by('-end_date', '-start_date')
            self.stdout.write(f'   🏢 CAREER PROGRESSION:')
            
            for j, exp in enumerate(experiences):
                end_str = 'Present' if not exp.end_date else exp.end_date.strftime('%b %Y')
                start_str = exp.start_date.strftime('%b %Y')
                
                self.stdout.write(f'      {j+1}. {exp.title} at {exp.organisation.name}')
                self.stdout.write(f'         📅 {start_str} → {end_str}')
                self.stdout.write(f'         📝 {exp.description[:100]}...')
                
                # Skills used in this role with temporal weights
                role_skills = exp.profile_experience_skills.all()
                if role_skills:
                    for skill_exp in role_skills:
                        weight = skill_exp.get_temporal_weight()
                        context = skill_exp.get_temporal_context()
                        self.stdout.write(f'         💡 {skill_exp.skill.name} (weight: {weight:.3f})')
                        self.stdout.write(f'            ⏰ {context}')
            
            # Overall skill portfolio
            all_skills = [ps.skill.name for ps in profile.profile_skills.all()]
            self.stdout.write(f'   🎯 SKILL PORTFOLIO: {", ".join(all_skills)}')

    def _show_sample_opportunities(self):
        self.stdout.write('\n\n🎯 ALL OPPORTUNITIES (Complete Requirements)')
        self.stdout.write('-' * 60)
        
        opportunities = Opportunity.objects.all()
        
        for i, opp in enumerate(opportunities, 1):
            self.stdout.write(f'\n{i}. 🏢 {opp.title} at {opp.organisation.name}')
            self.stdout.write(f'   📝 {opp.description[:150]}...')
            
            # Required skills
            required_skills = opp.opportunity_skills.filter(requirement_type='required')
            if required_skills.exists():
                self.stdout.write(f'   ✅ REQUIRED SKILLS:')
                for skill in required_skills:
                    self.stdout.write(f'      • {skill.skill.name}')
            
            # Preferred skills
            preferred_skills = opp.opportunity_skills.filter(requirement_type='preferred')
            if preferred_skills.exists():
                self.stdout.write(f'   🎯 PREFERRED SKILLS:')
                for skill in preferred_skills:
                    self.stdout.write(f'      • {skill.skill.name}')
            
            # Experience requirements
            exp_reqs = opp.opportunity_experiences.all()
            if exp_reqs.exists():
                self.stdout.write(f'   💼 EXPERIENCE REQUIREMENTS:')
                for exp_req in exp_reqs:
                    self.stdout.write(f'      • {exp_req.description[:80]}...')

    def _show_all_organizations(self):
        self.stdout.write('\n\n🏢 ALL ORGANIZATIONS IN SYSTEM')
        self.stdout.write('-' * 60)
        
        organizations = Organisation.objects.all().order_by('name')
        
        for org in organizations:
            self.stdout.write(f'   • {org.name}')

    def _show_all_skills(self):
        self.stdout.write('\n\n💡 ALL SKILLS IN SYSTEM')
        self.stdout.write('-' * 60)
        
        skills = Skill.objects.all().order_by('name')
        
        for skill in skills:
            self.stdout.write(f'   • {skill.name}')

    def _show_embedding_examples(self):
        self.stdout.write('\n\n🧠 EMBEDDING EXAMPLES (AI Vector Representations)')
        self.stdout.write('-' * 60)
        
        # Show different types of embedding texts
        
        # ProfileExperience embedding
        profile_exp = ProfileExperience.objects.first()
        if profile_exp:
            self.stdout.write(f'\n📊 ProfileExperience Embedding Text:')
            self.stdout.write(f'   "{profile_exp.get_embedding_text()}"')
            
        # ProfileSkill embedding
        profile_skill = ProfileSkill.objects.first()
        if profile_skill:
            self.stdout.write(f'\n👤 ProfileSkill Embedding Text:')
            self.stdout.write(f'   "{profile_skill.get_embedding_text()}"')
            
        # ProfileExperienceSkill embedding (with temporal context)
        exp_skill = ProfileExperienceSkill.objects.first()
        if exp_skill:
            self.stdout.write(f'\n🔗 ProfileExperienceSkill Embedding Text:')
            self.stdout.write(f'   "{exp_skill.get_embedding_text()}"')
            
        # OpportunitySkill embedding
        opp_skill = OpportunitySkill.objects.first()
        if opp_skill:
            self.stdout.write(f'\n🎯 OpportunitySkill Embedding Text:')
            self.stdout.write(f'   "{opp_skill.get_embedding_text()}"')

    def _show_opportunity_matches(self):
        self.stdout.write('\n\n🎯 OPPORTUNITIES → MATCHING PROFILES')
        self.stdout.write('-' * 60)
        
        opportunities = Opportunity.objects.all()
        
        for i, opp in enumerate(opportunities, 1):
            self.stdout.write(f'\n{i}. 🏢 {opp.title} at {opp.organisation.name}')
            
            # Get all evaluations for this opportunity, ordered by score
            evaluations = Evaluation.objects.filter(opportunity=opp).order_by('-final_score')
            
            if evaluations.exists():
                self.stdout.write(f'   👥 MATCHING PROFILES ({evaluations.count()} evaluated):')
                for eval in evaluations:
                    # Score interpretation
                    score_category = self._get_score_category(eval.final_score)
                    self.stdout.write(f'      #{eval.rank_in_set}. {eval.profile.first_name} {eval.profile.last_name} - Score: {eval.final_score:.3f} {score_category}')
                    
                    if eval.component_scores:
                        structured = eval.component_scores.get('structured', 0)
                        semantic = eval.component_scores.get('semantic', 0)
                        self.stdout.write(f'         📊 Structured: {structured:.3f} | Semantic: {semantic:.3f}')
                    
                    if eval.was_llm_judged and eval.llm_reasoning:
                        llm_score = eval.component_scores.get('llm_judge', eval.final_score)
                        self.stdout.write(f'         🧠 LLM Judge Score: {llm_score:.3f}')
                        self.stdout.write(f'         💭 LLM Reasoning: "{eval.llm_reasoning}"')
                        self.stdout.write('')  # Add spacing after LLM reasoning
            else:
                self.stdout.write(f'   👥 No evaluations run yet')

    def _show_profile_matches(self):
        self.stdout.write('\n\n👥 PROFILES → MATCHING OPPORTUNITIES')
        self.stdout.write('-' * 60)
        
        profiles = Profile.objects.all()
        
        for i, profile in enumerate(profiles, 1):
            self.stdout.write(f'\n{i}. 🧑 {profile.first_name} {profile.last_name}')
            
            # Get all evaluations for this profile, ordered by score
            evaluations = Evaluation.objects.filter(profile=profile).order_by('-final_score')
            
            if evaluations.exists():
                self.stdout.write(f'   🎯 MATCHING OPPORTUNITIES ({evaluations.count()} evaluated):')
                for eval in evaluations:
                    # Score interpretation
                    score_category = self._get_score_category(eval.final_score)
                    self.stdout.write(f'      #{eval.rank_in_set}. {eval.opportunity.title} at {eval.opportunity.organisation.name} - Score: {eval.final_score:.3f} {score_category}')
                    
                    if eval.component_scores:
                        structured = eval.component_scores.get('structured', 0)
                        semantic = eval.component_scores.get('semantic', 0)
                        self.stdout.write(f'         📊 Structured: {structured:.3f} | Semantic: {semantic:.3f}')
                    
                    if eval.was_llm_judged and eval.llm_reasoning:
                        llm_score = eval.component_scores.get('llm_judge', eval.final_score)
                        self.stdout.write(f'         🧠 LLM Judge Score: {llm_score:.3f}')
                        self.stdout.write(f'         💭 LLM Reasoning: "{eval.llm_reasoning}"')
                        self.stdout.write('')  # Add spacing after LLM reasoning
            else:
                self.stdout.write(f'   🎯 No evaluations run yet')

    def _show_temporal_weighting(self):
        self.stdout.write('\n\n⏰ TEMPORAL WEIGHTING DEMONSTRATION')
        self.stdout.write('-' * 60)
        
        # Show temporal weights for different experience skills
        exp_skills = ProfileExperienceSkill.objects.all()[:5]
        
        self.stdout.write('Skills ranked by temporal relevance (recent = higher weight):')
        
        # Sort by temporal weight
        weighted_skills = []
        for exp_skill in exp_skills:
            weight = exp_skill.get_temporal_weight()
            context = exp_skill.get_temporal_context()
            weighted_skills.append((exp_skill, weight, context))
        
        weighted_skills.sort(key=lambda x: x[1], reverse=True)
        
        for i, (exp_skill, weight, context) in enumerate(weighted_skills, 1):
            exp = exp_skill.profile_experience
            self.stdout.write(f'\n{i}. {exp_skill.skill.name} at {exp.organisation.name}')
            self.stdout.write(f'   ⚖️  Weight: {weight:.3f}')
            self.stdout.write(f'   📅 {context}')

    def _show_llm_reasoning_examples(self):
        """Show sample LLM reasoning from evaluations."""
        self.stdout.write('\n\n🧠 LLM EVALUATION EXAMPLES')
        self.stdout.write('-' * 60)
        
        # Get a few evaluations with LLM reasoning
        llm_evaluations = Evaluation.objects.filter(
            was_llm_judged=True,
            llm_reasoning__isnull=False
        ).exclude(llm_reasoning='').order_by('-final_score')[:3]
        
        if llm_evaluations.exists():
            for i, eval in enumerate(llm_evaluations, 1):
                llm_score = eval.component_scores.get('llm_judge', eval.final_score)
                score_category = self._get_score_category(eval.final_score)
                
                self.stdout.write(f'\n{i}. 🎯 {eval.profile.first_name} {eval.profile.last_name} → {eval.opportunity.title} at {eval.opportunity.organisation.name}')
                self.stdout.write(f'   📊 Final Score: {eval.final_score:.3f} {score_category}')
                self.stdout.write(f'   🧠 LLM Judge Score: {llm_score:.3f}')
                self.stdout.write(f'   💭 Reasoning: "{eval.llm_reasoning}"')
                
                if i < len(llm_evaluations):
                    self.stdout.write('')  # Add spacing between examples
        else:
            self.stdout.write('No LLM evaluations with reasoning found yet.')



    def _show_system_capabilities(self):
        self.stdout.write('\n\n🚀 SYSTEM CAPABILITIES SUMMARY')
        self.stdout.write('-' * 60)
        
        capabilities = [
            '✅ Multi-dimensional semantic matching (Skills, Experience, Context)',
            '✅ Temporal weighting (Recent experience weighted higher)',
            '✅ Evidence-based skill assessment (Stated, Experienced, Evidenced)',
            '✅ LLM-generated realistic ESG content',
            '✅ Bidirectional evaluation (Employer ↔ Candidate perspectives)',
            '✅ Cost-optimized pipeline (Structured → Semantic → LLM Judge)',
            '✅ Vector embeddings using OpenAI text-embedding-3-small',
            '✅ PostgreSQL pgvector for similarity search',
            '✅ ESG-focused career personas and skill taxonomy',
            '✅ Authentic career progression modeling',
        ]
        
        for capability in capabilities:
            self.stdout.write(f'   {capability}')
            
        self.stdout.write('\n🌟 Ready for production ESG talent matching!')
        
        # Embedding coverage
        profile_exp_with_embeddings = ProfileExperience.objects.exclude(embedding__isnull=True).count()
        total_profile_exp = ProfileExperience.objects.count()
        
        exp_skills_with_embeddings = ProfileExperienceSkill.objects.exclude(embedding__isnull=True).count()
        total_exp_skills = ProfileExperienceSkill.objects.count()
        
        self.stdout.write(f'\n📈 EMBEDDING COVERAGE:')
        self.stdout.write(f'   ProfileExperiences: {profile_exp_with_embeddings}/{total_profile_exp} ({profile_exp_with_embeddings/total_profile_exp*100:.1f}%)')
        self.stdout.write(f'   ProfileExperienceSkills: {exp_skills_with_embeddings}/{total_exp_skills} ({exp_skills_with_embeddings/total_exp_skills*100:.1f}%)')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('🎯 ESG TALENT MATCHING SYSTEM - DEMONSTRATION COMPLETE')
        self.stdout.write('=' * 80)
    
    def _get_score_category(self, score: float) -> str:
        """Return emoji-based score category interpretation."""
        if score >= 0.9:
            return "🔥 (Exceptional)"
        elif score >= 0.7:
            return "⭐ (Strong)"
        elif score >= 0.5:
            return "✅ (Good)"
        elif score >= 0.3:
            return "⚠️ (Moderate)"
        else:
            return "❌ (Weak)"