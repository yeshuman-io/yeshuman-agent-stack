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
        ]

        created_count = 0

        self.stdout.write('Creating deployment users...')

        # Create employer group if it doesn't exist
        from django.contrib.auth.models import Group
        employer_group, created = Group.objects.get_or_create(name='employer')
        self.stdout.write(f'Group "employer" {"created" if created else "already exists"}')

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

            # Add user to group
            user.groups.add(employer_group)

            created_count += 1
            self.stdout.write(f'Created deployment user: {email}')

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} deployment user(s)')
            )
        else:
            self.stdout.write('All deployment users already exist')
