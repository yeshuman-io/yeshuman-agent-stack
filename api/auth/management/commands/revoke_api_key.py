"""
Django management command to revoke API keys.

Usage:
    python manage.py revoke_api_key <key_id>
    python manage.py revoke_api_key --key "abc123..."
"""
from django.core.management.base import BaseCommand, CommandError
from auth.models import APIKey


class Command(BaseCommand):
    help = 'Revoke an API key'
    
    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            'key_id',
            nargs='?',
            type=int,
            help='ID of the API key to revoke'
        )
        group.add_argument(
            '--key',
            type=str,
            help='The actual API key value to revoke'
        )
    
    def handle(self, *args, **options):
        if options.get('key_id'):
            try:
                api_key = APIKey.objects.get(id=options['key_id'])
            except APIKey.DoesNotExist:
                raise CommandError(f'API key with ID {options["key_id"]} does not exist')
        
        elif options.get('key'):
            try:
                api_key = APIKey.objects.get(key=options['key'])
            except APIKey.DoesNotExist:
                raise CommandError('API key not found')
        
        # Check if already revoked
        if api_key.revoked_at:
            self.stdout.write(
                self.style.WARNING(f'API key "{api_key.name}" is already revoked')
            )
            return
        
        # Confirm revocation
        self.stdout.write(f'About to revoke API key:')
        self.stdout.write(f'  Name: {api_key.name}')
        self.stdout.write(f'  User: {api_key.user.username}')
        self.stdout.write(f'  Type: {api_key.key_type}')
        self.stdout.write(f'  Created: {api_key.created_at}')
        
        confirm = input('Are you sure you want to revoke this key? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Revocation cancelled.')
            return
        
        # Revoke the key
        api_key.revoke()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully revoked API key "{api_key.name}"')
        )

