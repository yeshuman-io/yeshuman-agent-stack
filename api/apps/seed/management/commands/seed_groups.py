"""
Django management command to seed user groups for TalentCo.
Creates the basic groups that control user focus and permissions.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Seed user groups for TalentCo user roles'

    def handle(self, *args, **options):
        """Create the basic user groups for TalentCo."""

        groups_data = [
            {
                'name': 'job_seeking',
                'description': 'Users focused on finding employment opportunities'
            },
            {
                'name': 'hiring',
                'description': 'Users focused on posting jobs and hiring talent'
            },
            {
                'name': 'system_administration',
                'description': 'System administrators with full access'
            }
        ]

        created_count = 0
        updated_count = 0

        for group_data in groups_data:
            group, created = Group.objects.get_or_create(
                name=group_data['name'],
                defaults={'name': group_data['name']}
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created group: {group.name} - {group_data["description"]}')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'Group already exists: {group.name}')
                )
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nGroups seeding complete: {created_count} created, {updated_count} already existed'
            )
        )

        # Summary
        self.stdout.write('\nAvailable Groups:')
        for group_data in groups_data:
            self.stdout.write(f'  - {group_data["name"]}: {group_data["description"]}')


