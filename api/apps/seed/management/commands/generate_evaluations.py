"""
Generate evaluation sets for all profiles and opportunities.
This creates the bidirectional matching data used by the system.
"""

from django.core.management.base import BaseCommand
from apps.profiles.models import Profile
from apps.opportunities.models import Opportunity
from apps.evaluations.services import EvaluationService
from apps.evaluations.models import EvaluationSet


class Command(BaseCommand):
    help = 'Generate evaluation sets for ESG talent matching demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing evaluations before generating new ones',
        )
        parser.add_argument(
            '--llm-threshold',
            type=float,
            default=0.7,
            help='Similarity score threshold for LLM judging (default: 0.7 = only matches above 70% similarity)',
        )
        parser.add_argument(
            '--profiles-only',
            action='store_true',
            help='Only generate opportunity evaluations for profiles (candidate perspective)',
        )
        parser.add_argument(
            '--opportunities-only',
            action='store_true',
            help='Only generate candidate evaluations for opportunities (employer perspective)',
        )

    def handle(self, *args, **options):
        clear_existing = options['clear_existing']
        llm_threshold = options['llm_threshold']
        profiles_only = options['profiles_only']
        opportunities_only = options['opportunities_only']

        self.stdout.write(
            self.style.SUCCESS(
                f'🎯 Generating ESG talent matching evaluations:\n'
                f'   🧠 LLM threshold: {llm_threshold:.1f} (similarity score threshold for detailed evaluation)\n'
                f'   🔄 Clear existing: {clear_existing}'
            )
        )

        try:
            if clear_existing:
                self._clear_existing_evaluations()

            # Get counts
            profile_count = Profile.objects.count()
            opportunity_count = Opportunity.objects.count()
            
            if profile_count == 0 or opportunity_count == 0:
                self.stdout.write(
                    self.style.ERROR(
                        '❌ No profiles or opportunities found. Run generate_esg_data first.'
                    )
                )
                return

            self.stdout.write(f'📊 Found {profile_count} profiles and {opportunity_count} opportunities')

            service = EvaluationService()
            created_eval_sets = []

            # Generate employer perspective evaluations (find candidates for each opportunity)
            if not profiles_only:
                self.stdout.write('\n🏢 EMPLOYER PERSPECTIVE: Finding candidates for opportunities...')
                opportunities = Opportunity.objects.all()
                
                for i, opportunity in enumerate(opportunities, 1):
                    self.stdout.write(f'   {i}/{opportunity_count}: {opportunity.title} at {opportunity.organisation.name}')
                    
                    eval_set = service.create_candidate_evaluation_set(
                        opportunity_id=str(opportunity.id),
                        llm_similarity_threshold=llm_threshold  # Direct similarity threshold
                    )
                    created_eval_sets.append(eval_set)
                    
                    self.stdout.write(f'      ✅ Evaluated {eval_set.total_evaluated} candidates')
                    self.stdout.write(f'      🧠 LLM judged: {eval_set.llm_judged_count} top performers')

            # Generate candidate perspective evaluations (find opportunities for each profile)  
            if not opportunities_only:
                self.stdout.write('\n👤 CANDIDATE PERSPECTIVE: Finding opportunities for profiles...')
                profiles = Profile.objects.all()
                
                for i, profile in enumerate(profiles, 1):
                    self.stdout.write(f'   {i}/{profile_count}: {profile.first_name} {profile.last_name}')
                    
                    eval_set = service.create_opportunity_evaluation_set(
                        profile_id=str(profile.id),
                        llm_similarity_threshold=llm_threshold  # Direct similarity threshold
                    )
                    created_eval_sets.append(eval_set)
                    
                    self.stdout.write(f'      ✅ Evaluated {eval_set.total_evaluated} opportunities')
                    self.stdout.write(f'      🧠 LLM judged: {eval_set.llm_judged_count} top matches')

            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Evaluation generation complete!\n'
                    f'   📊 Created: {len(created_eval_sets)} evaluation sets\n'
                    f'   🏢 Employer evaluations: {opportunity_count if not profiles_only else 0}\n'
                    f'   👤 Candidate evaluations: {profile_count if not opportunities_only else 0}\n'
                    f'   🧠 LLM threshold: {llm_threshold:.1f} (detailed reasoning for high-similarity matches)\n'
                    f'   ✅ Ready for matching system demonstration!'
                )
            )

            # Show summary statistics
            self._show_evaluation_summary()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error generating evaluations: {str(e)}')
            )
            raise

    def _clear_existing_evaluations(self):
        """Clear all existing evaluation data"""
        self.stdout.write('🗑️  Clearing existing evaluation data...')
        
        # Clear evaluations and evaluation sets
        from apps.evaluations.models import Evaluation, EvaluationSet
        eval_count = Evaluation.objects.count()
        eval_set_count = EvaluationSet.objects.count()
        
        Evaluation.objects.all().delete()
        EvaluationSet.objects.all().delete()
        
        self.stdout.write(f'   ✅ Deleted {eval_count} evaluations and {eval_set_count} evaluation sets')

    def _show_evaluation_summary(self):
        """Show summary of created evaluations"""
        from apps.evaluations.models import Evaluation, EvaluationSet
        
        self.stdout.write('\n📈 EVALUATION SUMMARY')
        self.stdout.write('-' * 50)
        
        total_eval_sets = EvaluationSet.objects.count()
        total_evaluations = Evaluation.objects.count()
        llm_judged = Evaluation.objects.filter(was_llm_judged=True).count()
        
        employer_sets = EvaluationSet.objects.filter(evaluator_perspective='employer').count()
        candidate_sets = EvaluationSet.objects.filter(evaluator_perspective='candidate').count()
        
        self.stdout.write(f'📊 Total evaluation sets: {total_eval_sets}')
        self.stdout.write(f'   🏢 Employer perspective: {employer_sets}')
        self.stdout.write(f'   👤 Candidate perspective: {candidate_sets}')
        self.stdout.write(f'📈 Total evaluations: {total_evaluations}')
        self.stdout.write(f'🧠 LLM judged evaluations: {llm_judged}')
        
        # Show top matches
        top_evaluations = Evaluation.objects.filter(was_llm_judged=True).order_by('-final_score')[:5]
        if top_evaluations.exists():
            self.stdout.write(f'\n⭐ Top 5 LLM-judged matches:')
            for i, eval in enumerate(top_evaluations, 1):
                self.stdout.write(f'   {i}. {eval.profile.first_name} {eval.profile.last_name} → {eval.opportunity.title}')
                self.stdout.write(f'      Score: {eval.final_score:.3f} | {eval.llm_reasoning[:100]}...')