from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create deployment users for Railway'

    def handle(self, *args, **options):
        User = get_user_model()

        # Deployment user credentials
        users = [
            ('daryl@yeshuman.io', 'abc'),
            ('seb@yeshuman.io', 'abc'),
            ('neil@talentco.io', 'abc'),
        ]

        created_count = 0

        self.stdout.write('Creating deployment users...')

        # Get all groups
        from django.contrib.auth.models import Group
        all_groups = Group.objects.all()
        self.stdout.write(f'Found {all_groups.count()} groups: {[g.name for g in all_groups]}')

        for email, password in users:
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(f'User {email} already exists - skipping')
                continue

            # Create the user (pass email as username since USERNAME_FIELD = 'email')
            user = User.objects.create_user(
                username=email,  # USERNAME_FIELD is 'email'
                email=email,
                password=password,
                is_staff=True,
                is_superuser=True
            )

            # Add user to all groups
            user.groups.set(all_groups)
            self.stdout.write(f'Added user {email} to groups: {[g.name for g in all_groups]}')

            created_count += 1
            self.stdout.write(f'Created deployment user: {email}')

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} deployment user(s)')
            )
        else:
            self.stdout.write('All deployment users already exist')
