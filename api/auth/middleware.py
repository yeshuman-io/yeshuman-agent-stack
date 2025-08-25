"""
Simple API Key authentication middleware for A2A and MCP protocols.
"""
import os
from django.http import JsonResponse
from django.conf import settings


class SimpleAPIKeyAuth:
    """Simple API key authentication middleware."""
    
    def __init__(self):
        """Initialize with API keys from environment."""
        # Parse API keys from environment (format: "name:key,name2:key2")
        a2a_keys_str = os.getenv('A2A_API_KEYS', '')
        self.a2a_api_keys = {}
        
        if a2a_keys_str:
            for key_pair in a2a_keys_str.split(','):
                if ':' in key_pair:
                    name, key = key_pair.strip().split(':', 1)
                    self.a2a_api_keys[key] = name
        
        # MCP uses single key
        self.mcp_api_key = os.getenv('MCP_API_KEY', '')
        
        # Auth enablement flags
        self.a2a_auth_enabled = os.getenv('A2A_AUTH_ENABLED', 'False').lower() == 'true'
        self.mcp_auth_enabled = os.getenv('MCP_AUTH_ENABLED', 'False').lower() == 'true'
    
    def authenticate_a2a(self, request):
        """Authenticate A2A requests."""
        if not self.a2a_auth_enabled:
            return True, None
            
        # Check X-API-Key header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return False, "Missing X-API-Key header"
            
        if api_key not in self.a2a_api_keys:
            return False, "Invalid API key"
            
        # Add authenticated client name to request
        request.authenticated_client = self.a2a_api_keys[api_key]
        return True, None
    
    def authenticate_mcp(self, request):
        """Authenticate MCP requests."""
        if not self.mcp_auth_enabled:
            return True, None
            
        # Check X-API-Key header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return False, "Missing X-API-Key header"
            
        if api_key != self.mcp_api_key:
            return False, "Invalid API key"
            
        return True, None
    
    def create_auth_error_response(self, error_message):
        """Create standardized auth error response."""
        return JsonResponse({
            'error': 'Authentication failed',
            'message': error_message
        }, status=401)


# Global auth instance
auth = SimpleAPIKeyAuth()


def require_a2a_auth(view_func):
    """Decorator to require A2A authentication."""
    def wrapper(request, *args, **kwargs):
        is_authenticated, error_message = auth.authenticate_a2a(request)
        if not is_authenticated:
            return auth.create_auth_error_response(error_message)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_mcp_auth(view_func):
    """Decorator to require MCP authentication."""
    def wrapper(request, *args, **kwargs):
        is_authenticated, error_message = auth.authenticate_mcp(request)
        if not is_authenticated:
            return auth.create_auth_error_response(error_message)
        return view_func(request, *args, **kwargs)
    return wrapper
