"""
Management command to review existing ESG synthetic data.
"""

from django.core.management.base import BaseCommand
from apps.seed.management.commands.generate_esg_data import Command as GenerateCommand


class Command(BaseCommand):
    help = 'Review existing ESG synthetic data without regenerating'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('📋 REVIEWING EXISTING ESG DATA')
        )
        
        # Reuse the review functionality from generate command
        generator_command = GenerateCommand()
        generator_command.stdout = self.stdout
        generator_command.style = self.style
        
        try:
            generator_command._show_detailed_review()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to review data: {e}')
            )