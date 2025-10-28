"""
Seed domain groups for a deployment.

Usage:
    ./manage.py seed_groups --domain employment
    ./manage.py seed_groups --domain travel
    ./manage.py seed_groups --domain health
    ./manage.py seed_groups --domain agency
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Seed user groups for a given domain (employment, travel, health, agency)'

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=str, required=True, choices=['employment', 'travel', 'health', 'agency'])

    def handle(self, *args, **options):
        domain = options['domain']

        if domain == 'employment':
            groups_data = [
                {'name': 'candidate', 'description': 'Job seeker'},
                {'name': 'employer', 'description': 'Hiring manager/employer'},
                {'name': 'recruiter', 'description': 'Talent partner/recruiter'},
                {'name': 'administrator', 'description': 'System administrator'},
            ]
        elif domain == 'travel':
            groups_data = [
                {'name': 'traveler', 'description': 'Traveler/customer'},
                {'name': 'agent', 'description': 'Travel agent/operator'},
            ]
        elif domain == 'health':
            groups_data = [
                {'name': 'patient', 'description': 'Health companion end-user'},
                {'name': 'practitioner', 'description': 'Health practitioner/coach'},
            ]
        else:  # agency
        groups_data = [
                {'name': 'client', 'description': 'Agency client partner'},
                {'name': 'engineer', 'description': 'Agency engineer'},
                {'name': 'principal', 'description': 'Agency principal (admin)'},
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

        self.stdout.write(self.style.SUCCESS(
            f"Seeded domain '{domain}' groups: {created_count} created, {updated_count} already existed"
        ))

        # Summary
        self.stdout.write('\nAvailable Groups:')
        for group_data in groups_data:
            self.stdout.write(f'  - {group_data["name"]}: {group_data["description"]}')


