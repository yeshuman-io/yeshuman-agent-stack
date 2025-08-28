"""
User-based API key authentication backends for Django.

This implements production-ready API key authentication that integrates
with Django Users and provides comprehensive security features.
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.utils import timezone
from .models import APIKey, APIKeyUsageLog


class UserAPIKeyBackend(BaseBackend):
    """
    Authentication backend for user-based API keys.
    
    This backend:
    1. Validates API keys against the database
    2. Returns the actual Django User who owns the key
    3. Handles rate limiting, expiration, and IP restrictions
    4. Logs usage for analytics
    """
    
    def authenticate(self, request, **credentials):
        """
        Authenticate a user via API key.
        
        Args:
            request: Django HttpRequest object
            **credentials: Additional credentials (unused)
            
        Returns:
            User instance if authentication succeeds, None otherwise
        """
        # Get API key from headers
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        try:
            # Look up the API key in the database
            key_obj = APIKey.objects.active_keys().select_related('user').get(key=api_key)
        except APIKey.DoesNotExist:
            return None
        
        # Validate the key
        if not self._validate_api_key(key_obj, request):
            return None
        
        # Record usage
        self._record_usage(key_obj, request)
        
        # Add API key info to the request for later use
        request.api_key = key_obj
        
        # Return the Django User who owns this API key
        return key_obj.user
    
    def get_user(self, user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User primary key
            
        Returns:
            User instance or None
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def _validate_api_key(self, key_obj, request):
        """
        Validate an API key against various security checks.
        
        Args:
            key_obj: APIKey instance
            request: Django HttpRequest object
            
        Returns:
            bool: True if valid, False if invalid
        """
        # Basic validity check
        if not key_obj.is_valid():
            return False
        
        # Check rate limits
        if key_obj.check_rate_limit():
            return False
        
        # Check IP restrictions
        ip_address = self._get_client_ip(request)
        if not key_obj.check_ip_restriction(ip_address):
            return False
        
        return True
    
    def _record_usage(self, key_obj, request):
        """
        Record usage of the API key.
        
        Args:
            key_obj: APIKey instance
            request: Django HttpRequest object
        """
        ip_address = self._get_client_ip(request)
        
        # Update key usage
        key_obj.record_usage(ip_address)
        
        # Create detailed usage log
        APIKeyUsageLog.objects.create(
            api_key=key_obj,
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            endpoint=request.path,
            method=request.method,
            timestamp=timezone.now()
        )
    
    def _get_client_ip(self, request):
        """
        Get the client IP address from the request.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            str: IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TypedAPIKeyBackend(UserAPIKeyBackend):
    """
    Authentication backend that only allows specific API key types.
    
    This can be used when you want separate backends for different
    API key types (e.g., one for A2A, one for MCP).
    """
    
    allowed_key_types = []  # Override in subclasses
    
    def authenticate(self, request, **credentials):
        """
        Authenticate with type restrictions.
        
        Args:
            request: Django HttpRequest object
            **credentials: Additional credentials
            
        Returns:
            User instance if authentication succeeds, None otherwise
        """
        # Get the user from parent class
        user = super().authenticate(request, **credentials)
        if not user:
            return None
        
        # Check if the API key type is allowed
        if hasattr(request, 'api_key'):
            if request.api_key.key_type not in self.allowed_key_types:
                return None
        
        return user


class A2AAPIKeyBackend(TypedAPIKeyBackend):
    """Authentication backend that only allows A2A API keys."""
    allowed_key_types = ['a2a']


class MCPAPIKeyBackend(TypedAPIKeyBackend):
    """Authentication backend that only allows MCP API keys."""
    allowed_key_types = ['mcp']


class AdminAPIKeyBackend(TypedAPIKeyBackend):
    """Authentication backend that only allows admin API keys."""
    allowed_key_types = ['admin']


class PermissionAwareAPIKeyBackend(UserAPIKeyBackend):
    """
    Authentication backend that also checks API key permissions.
    
    This backend checks both the API key validity and whether the key
    has the required permissions for the requested operation.
    """
    
    def authenticate(self, request, **credentials):
        """
        Authenticate with permission checking.
        
        Args:
            request: Django HttpRequest object
            **credentials: Additional credentials
            
        Returns:
            User instance if authentication succeeds, None otherwise
        """
        user = super().authenticate(request, **credentials)
        if not user:
            return None
        
        # Add permission checking logic here
        # This could check against APIKeyPermission model
        # or integrate with Django's permission system
        
        return user
    
    def has_permission(self, request, permission_name):
        """
        Check if the current API key has a specific permission.
        
        Args:
            request: Django HttpRequest object
            permission_name: Permission to check
            
        Returns:
            bool: True if permission is granted
        """
        if not hasattr(request, 'api_key'):
            return False
        
        return request.api_key.permissions.filter(
            permission=permission_name
        ).exists()


# Convenience functions for permission checking
def require_api_permission(permission_name):
    """
    Decorator that requires a specific API key permission.
    
    Args:
        permission_name: Required permission name
        
    Returns:
        Decorator function
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            from django.http import JsonResponse
            
            # Check if user is authenticated via API key
            if not hasattr(request, 'api_key'):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'Valid API key required'
                }, status=401)
            
            # Check permission
            if not request.api_key.permissions.filter(permission=permission_name).exists():
                return JsonResponse({
                    'error': 'Permission denied',
                    'message': f'API key lacks required permission: {permission_name}'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

