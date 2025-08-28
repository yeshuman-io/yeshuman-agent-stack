"""
Simple authentication module for YesHuman Agent Stack.

Provides environment variable-based API key authentication.
"""
from .middleware import require_a2a_auth, require_mcp_auth, require_api_key
from .backends import APIKeyUser

__all__ = ['require_a2a_auth', 'require_mcp_auth', 'require_api_key', 'APIKeyUser']
