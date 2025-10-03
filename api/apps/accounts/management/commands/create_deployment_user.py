from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


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

        with transaction.atomic():
            for email, password in users:
                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    self.stdout.write(
                        self.style.WARNING(f'User {email} already exists')
                    )
                    continue

                # Create the user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    is_staff=True,
                    is_superuser=True
                )

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created deployment user: {email}')
                )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} deployment user(s)')
            )
        else:
            self.stdout.write(
                self.style.INFO('All deployment users already exist')
            )
