"""
Django management command to create API keys.

Usage:
    python manage.py create_api_key username "My API Key" --type a2a --expires-in 30
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from auth.models import APIKey


class Command(BaseCommand):
    help = 'Create a new API key for a user'
    
    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user')
        parser.add_argument('name', type=str, help='Name for the API key')
        parser.add_argument(
            '--type',
            type=str,
            choices=['a2a', 'mcp', 'general', 'admin'],
            default='general',
            help='Type of API key (default: general)'
        )
        parser.add_argument(
            '--expires-in',
            type=int,
            help='Number of days until expiration (default: no expiration)'
        )
        parser.add_argument(
            '--rate-limit-hour',
            type=int,
            help='Maximum requests per hour'
        )
        parser.add_argument(
            '--rate-limit-day',
            type=int,
            help='Maximum requests per day'
        )
        parser.add_argument(
            '--usage-limit',
            type=int,
            help='Maximum total uses'
        )
        parser.add_argument(
            '--description',
            type=str,
            help='Description of the API key purpose'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        name = options['name']
        key_type = options['type']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        # Create the API key
        api_key, raw_key = APIKey.objects.create_key(
            user=user,
            name=name,
            key_type=key_type,
            expires_in_days=options.get('expires_in')
        )
        
        # Set optional fields
        if options.get('rate_limit_hour'):
            api_key.rate_limit_per_hour = options['rate_limit_hour']
        
        if options.get('rate_limit_day'):
            api_key.rate_limit_per_day = options['rate_limit_day']
        
        if options.get('usage_limit'):
            api_key.usage_limit = options['usage_limit']
        
        if options.get('description'):
            api_key.description = options['description']
        
        api_key.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created API key for {username}')
        )
        self.stdout.write(f'Name: {name}')
        self.stdout.write(f'Type: {key_type}')
        self.stdout.write(f'Key: {raw_key}')
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('⚠️  Save this key now! You won\'t be able to see it again.')
        )

