from django.core.management.base import BaseCommand
from django.db import transaction
from apps.organisations.models import Organisation
from apps.opportunities.models import Opportunity
from apps.applications.models import OpportunityQuestion, StageTemplate


class Command(BaseCommand):
    help = 'Seed sample opportunities with screening questions for testing the apply flow'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Get or create a sample organisation
            org, created = Organisation.objects.get_or_create(
                name="TechCorp Inc.",
                defaults={
                    'slug': 'techcorp-inc',
                    'description': 'A leading technology company',
                    'website': 'https://techcorp.com',
                    'industry': 'Technology'
                }
            )
            if created:
                self.stdout.write(f"Created organisation: {org.name}")
            else:
                self.stdout.write(f"Using existing organisation: {org.name}")

            # Create sample opportunities with screening questions
            opportunities_data = [
                {
                    'title': 'Senior Python Developer',
                    'description': 'We are looking for an experienced Python developer to join our backend team.',
                    'questions': [
                        {
                            'question_text': 'How many years of Python experience do you have?',
                            'question_type': 'number',
                            'is_required': True,
                            'min_value': 3,
                            'max_value': 20
                        },
                        {
                            'question_text': 'Describe a challenging Python project you worked on.',
                            'question_type': 'text',
                            'is_required': True
                        },
                        {
                            'question_text': 'Which Python frameworks have you used?',
                            'question_type': 'multiple_choice',
                            'is_required': False,
                            'options': ['Django', 'Flask', 'FastAPI', 'Pyramid', 'Other']
                        }
                    ]
                },
                {
                    'title': 'Frontend React Developer',
                    'description': 'Join our frontend team to build amazing user experiences with React.',
                    'questions': [
                        {
                            'question_text': 'How many years of React experience do you have?',
                            'question_type': 'number',
                            'is_required': True,
                            'min_value': 2,
                            'max_value': 15
                        },
                        {
                            'question_text': 'What is your favorite React hook and why?',
                            'question_type': 'text',
                            'is_required': False
                        }
                    ]
                }
            ]

            for opp_data in opportunities_data:
                # Create opportunity
                opp, opp_created = Opportunity.objects.get_or_create(
                    title=opp_data['title'],
                    organisation=org,
                    defaults={
                        'description': opp_data['description']
                    }
                )

                if opp_created:
                    self.stdout.write(f"Created opportunity: {opp.title}")

                    # Create screening questions
                    for q_data in opp_data['questions']:
                        config = {}
                        if 'options' in q_data:
                            config['options'] = q_data['options']
                        if 'min_value' in q_data or 'max_value' in q_data:
                            config['validation'] = {}
                            if 'min_value' in q_data:
                                config['validation']['min_value'] = q_data['min_value']
                            if 'max_value' in q_data:
                                config['validation']['max_value'] = q_data['max_value']

                        question = OpportunityQuestion.objects.create(
                            opportunity=opp,
                            question_text=q_data['question_text'],
                            question_type=q_data['question_type'],
                            is_required=q_data.get('is_required', False),
                            config=config
                        )
                        self.stdout.write(f"  Created question: {question.question_text}")
                else:
                    self.stdout.write(f"Opportunity already exists: {opp.title}")

            self.stdout.write(self.style.SUCCESS('Successfully seeded sample opportunities with screening questions!'))

            # Show summary
            total_opps = Opportunity.objects.filter(organisation=org).count()
            total_questions = OpportunityQuestion.objects.filter(opportunity__organisation=org).count()
            self.stdout.write(f"Summary: {total_opps} opportunities with {total_questions} screening questions")
