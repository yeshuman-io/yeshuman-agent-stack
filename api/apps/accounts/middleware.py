"""
Django middleware for API key authentication.

This middleware works with the custom authentication backends to provide
automatic authentication for API requests.
"""
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class APIKeyAuthenticationMiddleware(MiddlewareMixin):
    """
    Django middleware that automatically authenticates API key requests.
    
    This middleware works with the authentication backends to automatically
    authenticate requests that include valid API keys in the X-API-Key header.
    """
    
    def process_request(self, request):
        """
        Process incoming request and attempt API key authentication.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            None to continue processing, or HttpResponse to short-circuit
        """
        # Skip authentication for certain paths
        if self._should_skip_auth(request):
            return None
        
        # Only attempt authentication if X-API-Key header is present
        if 'HTTP_X_API_KEY' not in request.META:
            return None
        
        # Attempt authentication using the custom backends
        user = authenticate(request)
        if user:
            request.user = user
            # Add convenience attributes for backward compatibility
            if hasattr(user, 'client_name'):
                request.authenticated_client = user.client_name
                request.api_key_type = user.api_key_type
        
        return None
    
    def _should_skip_auth(self, request):
        """
        Determine if authentication should be skipped for this request.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            bool: True if authentication should be skipped
        """
        # Skip authentication for Django admin and static files
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        return any(request.path.startswith(path) for path in skip_paths)


class APIKeyRequiredMixin:
    """
    Mixin for views that require API key authentication.
    
    Usage:
        class MyAPIView(APIKeyRequiredMixin, View):
            allowed_api_key_types = ['a2a', 'mcp']  # Optional: restrict to specific types
            
            def get(self, request):
                # request.user will be an APIKeyUser instance
                return JsonResponse({'client': request.user.client_name})
    """
    
    allowed_api_key_types = None  # None means allow all types
    
    def dispatch(self, request, *args, **kwargs):
        """
        Check API key authentication before dispatching to view method.
        
        Args:
            request: Django HttpRequest object
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            HttpResponse from view method or authentication error
        """
        from apps.accounts.backends import APIKeyUser
        
        # Check if user is authenticated via API key
        if not isinstance(request.user, APIKeyUser):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid X-API-Key header required'
            }, status=401)
        
        # Check if API key type is allowed (if restriction is set)
        if (self.allowed_api_key_types and 
            request.user.api_key_type not in self.allowed_api_key_types):
            return JsonResponse({
                'error': 'Unauthorized',
                'message': f'API key type "{request.user.api_key_type}" not allowed for this endpoint'
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


# Decorator functions for backward compatibility
def require_api_key(allowed_types=None):
    """
    Decorator that requires API key authentication for a view.
    
    Args:
        allowed_types: List of allowed API key types (None for all)
        
    Returns:
        Decorated view function
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            from apps.accounts.backends import APIKeyUser
            
            # Check if user is authenticated via API key
            if not isinstance(request.user, APIKeyUser):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'Valid X-API-Key header required'
                }, status=401)
            
            # Check if API key type is allowed
            if (allowed_types and 
                request.user.api_key_type not in allowed_types):
                return JsonResponse({
                    'error': 'Unauthorized',
                    'message': f'API key type "{request.user.api_key_type}" not allowed'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_a2a_auth(view_func):
    """
    Decorator that requires A2A API key authentication.
    
    Args:
        view_func: View function to decorate
        
    Returns:
        Decorated view function
    """
    return require_api_key(['a2a'])(view_func)


def require_mcp_auth(view_func):
    """
    Decorator that requires MCP API key authentication.
    
    Args:
        view_func: View function to decorate
        
    Returns:
        Decorated view function
    """
    return require_api_key(['mcp'])(view_func)


