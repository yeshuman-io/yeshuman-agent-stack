"""
Django authentication backends for API key authentication.

Following Django 5.1 patterns for custom authentication backends.
"""
import os
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

User = get_user_model()


class APIKeyUser(AnonymousUser):
    """
    Custom user class for API key authentication.
    Extends AnonymousUser but adds API key identification.
    """
    def __init__(self, client_name, api_key_type):
        super().__init__()
        self.client_name = client_name
        self.api_key_type = api_key_type  # 'a2a' or 'mcp'
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def __str__(self):
        return f"APIKeyUser({self.client_name}, {self.api_key_type})"


class A2AAPIKeyBackend(BaseBackend):
    """
    Authentication backend for A2A protocol API keys.
    
    Authenticates using X-API-Key header against A2A_API_KEYS environment variable.
    """
    
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
        
        # Auth enablement flag
        self.auth_enabled = os.getenv('A2A_AUTH_ENABLED', 'False').lower() == 'true'
    
    def authenticate(self, request, **credentials):
        """
        Authenticate A2A API key from request headers.
        
        Args:
            request: Django HttpRequest object
            **credentials: Additional credentials (unused for API key auth)
            
        Returns:
            APIKeyUser instance if authentication succeeds, None otherwise
        """
        # Skip authentication if disabled
        if not self.auth_enabled:
            return None
        
        # Check for X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        # Validate API key
        if api_key in self.a2a_api_keys:
            client_name = self.a2a_api_keys[api_key]
            return APIKeyUser(client_name=client_name, api_key_type='a2a')
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID. Not applicable for API key authentication.
        
        Args:
            user_id: User ID (unused for API key auth)
            
        Returns:
            None (API key users are not persistent)
        """
        return None


class MCPAPIKeyBackend(BaseBackend):
    """
    Authentication backend for MCP protocol API keys.
    
    Authenticates using X-API-Key header against MCP_API_KEY environment variable.
    """
    
    def __init__(self):
        """Initialize with API key from environment."""
        self.mcp_api_key = os.getenv('MCP_API_KEY', '')
        self.auth_enabled = os.getenv('MCP_AUTH_ENABLED', 'False').lower() == 'true'
    
    def authenticate(self, request, **credentials):
        """
        Authenticate MCP API key from request headers.
        
        Args:
            request: Django HttpRequest object
            **credentials: Additional credentials (unused for API key auth)
            
        Returns:
            APIKeyUser instance if authentication succeeds, None otherwise
        """
        # Skip authentication if disabled
        if not self.auth_enabled:
            return None
        
        # Check for X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        # Validate API key
        if api_key == self.mcp_api_key:
            return APIKeyUser(client_name='mcp_client', api_key_type='mcp')
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID. Not applicable for API key authentication.
        
        Args:
            user_id: User ID (unused for API key auth)
            
        Returns:
            None (API key users are not persistent)
        """
        return None


class UniversalAPIKeyBackend(BaseBackend):
    """
    Universal authentication backend that handles both A2A and MCP API keys.
    
    This is a more convenient backend that combines both A2A and MCP authentication
    into a single backend class.
    """
    
    def __init__(self):
        """Initialize with API keys from environment."""
        # A2A API keys (format: "name:key,name2:key2")
        a2a_keys_str = os.getenv('A2A_API_KEYS', '')
        self.a2a_api_keys = {}
        
        if a2a_keys_str:
            for key_pair in a2a_keys_str.split(','):
                if ':' in key_pair:
                    name, key = key_pair.strip().split(':', 1)
                    self.a2a_api_keys[key] = name
        
        # MCP API key
        self.mcp_api_key = os.getenv('MCP_API_KEY', '')
        
        # Auth enablement flags
        self.a2a_auth_enabled = os.getenv('A2A_AUTH_ENABLED', 'False').lower() == 'true'
        self.mcp_auth_enabled = os.getenv('MCP_AUTH_ENABLED', 'False').lower() == 'true'
    
    def authenticate(self, request, **credentials):
        """
        Authenticate API key from request headers for both A2A and MCP protocols.
        
        Args:
            request: Django HttpRequest object
            **credentials: Additional credentials (unused for API key auth)
            
        Returns:
            APIKeyUser instance if authentication succeeds, None otherwise
        """
        # Get API key from headers
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        # Try A2A authentication first
        if self.a2a_auth_enabled and api_key in self.a2a_api_keys:
            client_name = self.a2a_api_keys[api_key]
            return APIKeyUser(client_name=client_name, api_key_type='a2a')
        
        # Try MCP authentication
        if self.mcp_auth_enabled and api_key == self.mcp_api_key:
            return APIKeyUser(client_name='mcp_client', api_key_type='mcp')
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID. Not applicable for API key authentication.
        
        Args:
            user_id: User ID (unused for API key auth)
            
        Returns:
            None (API key users are not persistent)
        """
        return None
