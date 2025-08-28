"""
Django management command to list API keys.

Usage:
    python manage.py list_api_keys
    python manage.py list_api_keys --user username
    python manage.py list_api_keys --type a2a
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from auth.models import APIKey
from django.utils import timezone


class Command(BaseCommand):
    help = 'List API keys'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by username'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['a2a', 'mcp', 'general', 'admin'],
            help='Filter by key type'
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active keys'
        )
        parser.add_argument(
            '--expired',
            action='store_true',
            help='Show only expired keys'
        )
    
    def handle(self, *args, **options):
        queryset = APIKey.objects.select_related('user').order_by('-created_at')
        
        # Apply filters
        if options.get('user'):
            try:
                user = User.objects.get(username=options['user'])
                queryset = queryset.filter(user=user)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{options["user"]}" does not exist')
                )
                return
        
        if options.get('type'):
            queryset = queryset.filter(key_type=options['type'])
        
        if options.get('active_only'):
            queryset = queryset.filter(is_active=True, revoked_at__isnull=True)
            now = timezone.now()
            queryset = queryset.filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
            )
        
        if options.get('expired'):
            now = timezone.now()
            queryset = queryset.filter(expires_at__lte=now)
        
        if not queryset.exists():
            self.stdout.write('No API keys found.')
            return
        
        # Display keys
        self.stdout.write(f'Found {queryset.count()} API key(s):')
        self.stdout.write('')
        
        for key in queryset:
            status = self._get_key_status(key)
            
            self.stdout.write(f'🔑 {key.name}')
            self.stdout.write(f'   User: {key.user.username}')
            self.stdout.write(f'   Type: {key.key_type}')
            self.stdout.write(f'   Key: {key.key[:8]}...{key.key[-4:]}')
            self.stdout.write(f'   Status: {status}')
            self.stdout.write(f'   Created: {key.created_at.strftime("%Y-%m-%d %H:%M")}')
            
            if key.last_used_at:
                self.stdout.write(f'   Last used: {key.last_used_at.strftime("%Y-%m-%d %H:%M")}')
            else:
                self.stdout.write('   Last used: Never')
            
            if key.expires_at:
                self.stdout.write(f'   Expires: {key.expires_at.strftime("%Y-%m-%d %H:%M")}')
            
            self.stdout.write(f'   Usage: {key.usage_count}')
            
            if key.description:
                self.stdout.write(f'   Description: {key.description}')
            
            self.stdout.write('')
    
    def _get_key_status(self, key):
        """Get human-readable status of an API key."""
        if key.revoked_at:
            return self.style.ERROR('REVOKED')
        elif not key.is_active:
            return self.style.ERROR('INACTIVE')
        elif key.is_expired():
            return self.style.ERROR('EXPIRED')
        elif key.usage_limit and key.usage_count >= key.usage_limit:
            return self.style.ERROR('USAGE_LIMIT_REACHED')
        else:
            return self.style.SUCCESS('ACTIVE')

