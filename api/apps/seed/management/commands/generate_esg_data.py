"""
Management command to generate realistic ESG synthetic data.
"""

import random
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.seed.factories import ESGProfileBuilder, ESGOpportunityBuilder, SkillFactory, OrganisationFactory
from apps.seed.esg_definitions import ESG_PERSONAS, ESG_INDUSTRIES
from apps.embeddings.services import generate_all_embeddings


class Command(BaseCommand):
    help = 'Generate realistic ESG synthetic data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--profiles',
            type=int,
            default=25,
            help='Number of profiles to generate (default: 25)',
        )
        parser.add_argument(
            '--opportunities',
            type=int,
            default=15,
            help='Number of opportunities to generate (default: 15)',
        )
        parser.add_argument(
            '--skip-embeddings',
            action='store_true',
            help='Skip embedding generation (faster for testing)',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before generating',
        )
        parser.add_argument(
            '--review',
            action='store_true',
            help='Show detailed review of generated data',
        )

    def handle(self, *args, **options):
        num_profiles = options['profiles']
        num_opportunities = options['opportunities']
        skip_embeddings = options['skip_embeddings']
        clear_existing = options['clear_existing']
        show_review = options['review']

        self.stdout.write(
            self.style.SUCCESS(
                f'🌱 Generating ESG synthetic data:\n'
                f'   📊 Profiles: {num_profiles}\n'
                f'   💼 Opportunities: {num_opportunities}\n'
                f'   🔗 Embeddings: {"Skipped" if skip_embeddings else "Included"}'
            )
        )

        try:
            if clear_existing:
                self._clear_existing_data()

            # Phase 1: Create base data (skills, organizations)
            self.stdout.write('📚 Creating ESG skills and organizations...')
            self._create_base_data()

            # Phase 2: Generate ESG profiles with realistic career progression
            self.stdout.write(f'👥 Generating {num_profiles} ESG professional profiles...')
            profiles = self._generate_profiles(num_profiles)

            # Phase 3: Generate ESG opportunities 
            self.stdout.write(f'💼 Generating {num_opportunities} ESG opportunities...')
            opportunities = self._generate_opportunities(num_opportunities)

            # Phase 4: Generate embeddings
            if not skip_embeddings:
                self.stdout.write('🧠 Generating embeddings for semantic matching...')
                self._generate_embeddings()

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ ESG synthetic data generation complete!\n'
                    f'   👥 Created: {len(profiles)} profiles\n'
                    f'   💼 Created: {len(opportunities)} opportunities\n'
                    f'   🎯 Ready for evaluation pipeline testing'
                )
            )

            # Show detailed review if requested
            if show_review:
                self.stdout.write('\n' + '='*80)
                self.stdout.write(self.style.SUCCESS('📋 DETAILED REVIEW OF GENERATED DATA'))
                self.stdout.write('='*80)
                self._show_detailed_review()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to generate ESG data: {e}')
            )
            raise

    def _clear_existing_data(self):
        """Clear existing synthetic data"""
        from apps.profiles.models import Profile
        from apps.opportunities.models import Opportunity
        from apps.skills.models import Skill
        from apps.organisations.models import Organisation

        self.stdout.write('🧹 Clearing existing data...')
        
        # Clear in proper order to respect foreign keys
        Profile.objects.all().delete()
        Opportunity.objects.all().delete()
        Skill.objects.all().delete()
        Organisation.objects.all().delete()

    def _create_base_data(self):
        """Create foundational skills and organizations"""
        
        # Create ESG skills (factory will handle duplicates)
        skills_created = 0
        for _ in range(100):  # Create all ESG skills
            try:
                SkillFactory()
                skills_created += 1
            except:
                pass  # Skill already exists
        
        # Create ESG organizations
        orgs_created = 0
        for _ in range(50):  # Create all ESG organizations
            try:
                OrganisationFactory()
                orgs_created += 1
            except:
                pass  # Organization already exists

        self.stdout.write(f'   📚 Skills: {skills_created} created')
        self.stdout.write(f'   🏢 Organizations: {orgs_created} created')

    def _generate_profiles(self, num_profiles: int) -> list:
        """Generate realistic ESG professional profiles"""
        builder = ESGProfileBuilder()
        profiles = []
        
        # Distribute profiles across personas
        persona_names = list(ESG_PERSONAS.keys())
        persona_distribution = self._calculate_persona_distribution(num_profiles, len(persona_names))
        
        for persona_name, count in zip(persona_names, persona_distribution):
            self.stdout.write(f'   👤 Creating {count} {persona_name} profiles...')
            
            for _ in range(count):
                try:
                    profile = builder.build_esg_profile(persona_name)
                    profiles.append(profile)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️  Failed to create {persona_name} profile: {e}')
                    )

        return profiles

    def _generate_opportunities(self, num_opportunities: int) -> list:
        """Generate realistic ESG opportunities"""
        builder = ESGOpportunityBuilder()
        opportunities = []
        
        # Distribute opportunities across industries
        industries = list(ESG_INDUSTRIES.keys())
        industry_distribution = self._calculate_persona_distribution(num_opportunities, len(industries))
        
        for industry, count in zip(industries, industry_distribution):
            self.stdout.write(f'   💼 Creating {count} {industry} opportunities...')
            
            for _ in range(count):
                try:
                    # Mix of seniority levels
                    seniority = random.choice(['entry', 'mid', 'senior'])
                    opportunity = builder.build_esg_opportunity(industry, seniority)
                    opportunities.append(opportunity)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️  Failed to create {industry} opportunity: {e}')
                    )

        return opportunities

    def _calculate_persona_distribution(self, total: int, num_categories: int) -> list:
        """Calculate how to distribute total items across categories"""
        base_count = total // num_categories
        remainder = total % num_categories
        
        distribution = [base_count] * num_categories
        
        # Distribute remainder randomly
        for i in random.sample(range(num_categories), remainder):
            distribution[i] += 1
            
        return distribution

    def _generate_embeddings(self):
        """Generate embeddings for all created data"""
        try:
            generate_all_embeddings(force_regenerate=False)
            self.stdout.write('   🧠 Embeddings generated successfully')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  Embedding generation failed: {e}')
            )

    def _show_detailed_review(self):
        """Show detailed review of all generated data"""
        from apps.profiles.models import Profile, ProfileExperience, ProfileSkill, ProfileExperienceSkill
        from apps.opportunities.models import Opportunity, OpportunitySkill, OpportunityExperience
        from apps.skills.models import Skill
        from apps.organisations.models import Organisation

        # Show profiles with full details
        self.stdout.write(f'\n👥 {self.style.HTTP_INFO("PROFILES GENERATED")}')
        self.stdout.write('-' * 60)
        
        for i, profile in enumerate(Profile.objects.all()[:10], 1):  # Show first 10
            self.stdout.write(f'\n📋 Profile {i}: {profile.first_name} {profile.last_name}')
            self.stdout.write(f'   📧 Email: {profile.email}')
            
            # Show experiences
            experiences = profile.profile_experiences.all().order_by('-end_date')
            self.stdout.write(f'   💼 Experiences ({experiences.count()}):')
            for exp in experiences:
                duration = f"{exp.start_date} to {'Present' if not exp.end_date else exp.end_date}"
                self.stdout.write(f'      • {exp.title} at {exp.organisation.name} ({duration})')
                if exp.description:
                    desc_preview = exp.description[:100] + "..." if len(exp.description) > 100 else exp.description
                    self.stdout.write(f'        Description: {desc_preview}')
                
                # Show skills for this experience
                exp_skills = exp.profile_experience_skills.all()
                if exp_skills:
                    skills_list = [pes.skill.name for pes in exp_skills[:5]]  # First 5 skills
                    self.stdout.write(f'        Skills: {", ".join(skills_list)}')
            
            # Show profile-level skills
            profile_skills = profile.profile_skills.all()
            self.stdout.write(f'   🎯 Skills ({profile_skills.count()}):')
            for ps in profile_skills[:8]:  # Show first 8 skills
                self.stdout.write(f'      • {ps.skill.name} ({ps.evidence_level})')
            
            if profile.profile_skills.count() > 8:
                self.stdout.write(f'      ... and {profile.profile_skills.count() - 8} more skills')

        # Show opportunities
        self.stdout.write(f'\n\n💼 {self.style.HTTP_INFO("OPPORTUNITIES GENERATED")}')
        self.stdout.write('-' * 60)
        
        for i, opportunity in enumerate(Opportunity.objects.all(), 1):
            self.stdout.write(f'\n📋 Opportunity {i}: {opportunity.title}')
            self.stdout.write(f'   🏢 Company: {opportunity.organisation.name}')
            
            # Show description preview
            if opportunity.description:
                desc_preview = opportunity.description[:150] + "..." if len(opportunity.description) > 150 else opportunity.description
                self.stdout.write(f'   📝 Description: {desc_preview}')
            
            # Show required skills
            required_skills = opportunity.opportunity_skills.filter(requirement_type='required')
            if required_skills:
                skills_list = [os.skill.name for os in required_skills[:5]]
                self.stdout.write(f'   ✅ Required Skills: {", ".join(skills_list)}')
            
            # Show preferred skills
            preferred_skills = opportunity.opportunity_skills.filter(requirement_type='preferred')
            if preferred_skills:
                skills_list = [os.skill.name for os in preferred_skills[:5]]
                self.stdout.write(f'   🎯 Preferred Skills: {", ".join(skills_list)}')
            
            # Show experience requirements
            exp_reqs = opportunity.opportunity_experiences.all()
            if exp_reqs:
                for req in exp_reqs:
                    req_preview = req.description[:100] + "..." if len(req.description) > 100 else req.description
                    self.stdout.write(f'   📊 Experience Req: {req_preview}')

        # Show summary statistics
        self.stdout.write(f'\n\n📊 {self.style.HTTP_INFO("SUMMARY STATISTICS")}')
        self.stdout.write('-' * 60)
        
        total_profiles = Profile.objects.count()
        total_experiences = ProfileExperience.objects.count()
        total_profile_skills = ProfileSkill.objects.count()
        total_exp_skills = ProfileExperienceSkill.objects.count()
        total_opportunities = Opportunity.objects.count()
        total_opp_skills = OpportunitySkill.objects.count()
        total_opp_exp = OpportunityExperience.objects.count()
        total_skills = Skill.objects.count()
        total_orgs = Organisation.objects.count()
        
        self.stdout.write(f'👥 Profiles: {total_profiles}')
        self.stdout.write(f'💼 Experiences: {total_experiences} (avg {total_experiences/total_profiles:.1f} per profile)')
        self.stdout.write(f'🎯 Profile Skills: {total_profile_skills} (avg {total_profile_skills/total_profiles:.1f} per profile)')
        self.stdout.write(f'🔗 Experience-Skills: {total_exp_skills}')
        self.stdout.write(f'💼 Opportunities: {total_opportunities}')
        self.stdout.write(f'✅ Opportunity Skills: {total_opp_skills} (avg {total_opp_skills/total_opportunities:.1f} per opportunity)')
        self.stdout.write(f'📊 Opportunity Experience Reqs: {total_opp_exp}')
        self.stdout.write(f'📚 Total Skills in Taxonomy: {total_skills}')
        self.stdout.write(f'🏢 Total Organizations: {total_orgs}')

        # Show embedding status
        profiles_with_embeddings = ProfileExperience.objects.exclude(embedding__isnull=True).count()
        skills_with_embeddings = ProfileSkill.objects.exclude(embedding__isnull=True).count()
        exp_skills_with_embeddings = ProfileExperienceSkill.objects.exclude(embedding__isnull=True).count()
        
        self.stdout.write(f'\n🧠 Embedding Coverage:')
        self.stdout.write(f'   ProfileExperiences: {profiles_with_embeddings}/{total_experiences} ({profiles_with_embeddings/total_experiences*100:.1f}%)')
        self.stdout.write(f'   ProfileSkills: {skills_with_embeddings}/{total_profile_skills} ({skills_with_embeddings/total_profile_skills*100:.1f}%)')
        self.stdout.write(f'   ProfileExperienceSkills: {exp_skills_with_embeddings}/{total_exp_skills} ({exp_skills_with_embeddings/total_exp_skills*100:.1f}%)')

        # Show sample embedding texts
        self.stdout.write(f'\n\n🧠 {self.style.HTTP_INFO("SAMPLE EMBEDDING TEXTS")}')
        self.stdout.write('-' * 60)
        
        # Sample ProfileExperience embedding text
        sample_exp = ProfileExperience.objects.first()
        if sample_exp:
            self.stdout.write(f'\n📊 ProfileExperience embedding text:')
            self.stdout.write(f'"{sample_exp.get_embedding_text()}"')
        
        # Sample ProfileSkill embedding text
        sample_skill = ProfileSkill.objects.first()
        if sample_skill:
            self.stdout.write(f'\n🎯 ProfileSkill embedding text:')
            self.stdout.write(f'"{sample_skill.get_embedding_text()}"')
        
        # Sample OpportunitySkill embedding text
        sample_opp_skill = OpportunitySkill.objects.first()
        if sample_opp_skill:
            self.stdout.write(f'\n✅ OpportunitySkill embedding text:')
            self.stdout.write(f'"{sample_opp_skill.get_embedding_text()}"')

        self.stdout.write(f'\n' + '='*80)