"""
Django models for user-based API key authentication.

This implements a production-ready API key system tied to Django Users.
"""
import secrets
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class APIKeyManager(models.Manager):
    """Custom manager for APIKey model."""
    
    def create_key(self, user, name, key_type='general', expires_in_days=None):
        """
        Create a new API key for a user.
        
        Args:
            user: Django User instance
            name: Human-readable name for the key
            key_type: Type of API key ('a2a', 'mcp', 'general')
            expires_in_days: Number of days until expiration (None for no expiration)
            
        Returns:
            Tuple of (APIKey instance, raw_key_string)
        """
        raw_key = self._generate_key()
        
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        api_key = self.create(
            user=user,
            name=name,
            key_type=key_type,
            key=raw_key,
            expires_at=expires_at
        )
        
        return api_key, raw_key
    
    def _generate_key(self, length=32):
        """Generate a secure random API key."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def active_keys(self):
        """Return only active (non-expired, non-revoked) API keys."""
        now = timezone.now()
        return self.filter(
            is_active=True,
            revoked_at__isnull=True
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )


class APIKey(models.Model):
    """
    API Key model for user-based authentication.
    
    Each API key belongs to a Django User and can have specific permissions
    and expiration dates.
    """
    
    KEY_TYPES = [
        ('a2a', 'Agent-to-Agent'),
        ('mcp', 'Model Context Protocol'),
        ('general', 'General API Access'),
        ('admin', 'Administrative Access'),
    ]
    
    # Core fields
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='api_keys',
        help_text="The user this API key belongs to"
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name for this API key"
    )
    key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="The actual API key value"
    )
    key_type = models.CharField(
        max_length=20,
        choices=KEY_TYPES,
        default='general',
        help_text="Type/purpose of this API key"
    )
    
    # Status and lifecycle
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this key is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this key was last used for authentication"
    )
    expires_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this key expires (null for no expiration)"
    )
    revoked_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this key was revoked (if applicable)"
    )
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this key has been used"
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of uses (null for unlimited)"
    )
    
    # Rate limiting
    rate_limit_per_hour = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum requests per hour (null for no limit)"
    )
    rate_limit_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum requests per day (null for no limit)"
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        help_text="Optional description of this API key's purpose"
    )
    allowed_ips = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed IP addresses (empty for no restriction)"
    )
    
    objects = APIKeyManager()
    
    class Meta:
        db_table = 'auth_api_keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['key_type', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.key_type})"
    
    def is_valid(self):
        """Check if this API key is currently valid."""
        if not self.is_active or self.revoked_at:
            return False
        
        # Check expiration
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        # Check usage limit
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        
        return True
    
    def is_expired(self):
        """Check if this API key has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def revoke(self):
        """Revoke this API key."""
        self.revoked_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['revoked_at', 'is_active'])
    
    def record_usage(self, ip_address=None):
        """Record a usage of this API key."""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
        
        # Create usage log entry
        APIKeyUsageLog.objects.create(
            api_key=self,
            ip_address=ip_address,
            timestamp=timezone.now()
        )
    
    def check_rate_limit(self):
        """
        Check if this API key has exceeded its rate limits.
        
        Returns:
            bool: True if rate limit is exceeded, False otherwise
        """
        now = timezone.now()
        
        # Check hourly rate limit
        if self.rate_limit_per_hour:
            hour_ago = now - timedelta(hours=1)
            hourly_usage = APIKeyUsageLog.objects.filter(
                api_key=self,
                timestamp__gte=hour_ago
            ).count()
            
            if hourly_usage >= self.rate_limit_per_hour:
                return True
        
        # Check daily rate limit
        if self.rate_limit_per_day:
            day_ago = now - timedelta(days=1)
            daily_usage = APIKeyUsageLog.objects.filter(
                api_key=self,
                timestamp__gte=day_ago
            ).count()
            
            if daily_usage >= self.rate_limit_per_day:
                return True
        
        return False
    
    def check_ip_restriction(self, ip_address):
        """
        Check if the given IP address is allowed for this API key.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            bool: True if IP is allowed, False if restricted
        """
        if not self.allowed_ips:
            return True  # No restrictions
        
        return ip_address in self.allowed_ips


class APIKeyUsageLog(models.Model):
    """
    Log of API key usage for analytics and rate limiting.
    """
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    endpoint = models.CharField(max_length=200, blank=True)
    method = models.CharField(max_length=10, blank=True)
    
    class Meta:
        db_table = 'auth_api_key_usage_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['api_key', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.api_key.name} used at {self.timestamp}"


class APIKeyPermission(models.Model):
    """
    Specific permissions for API keys.
    
    This allows fine-grained control over what each API key can access.
    """
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    permission = models.CharField(
        max_length=100,
        help_text="Permission name (e.g., 'a2a.send_message', 'mcp.list_tools')"
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_api_key_permissions'
        unique_together = ['api_key', 'permission']
    
    def __str__(self):
        return f"{self.api_key.name} - {self.permission}"

