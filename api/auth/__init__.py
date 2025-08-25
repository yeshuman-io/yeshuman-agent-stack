"""
Authentication module for YesHuman Agent Stack.
"""
from .middleware import require_a2a_auth, require_mcp_auth, auth

__all__ = ['require_a2a_auth', 'require_mcp_auth', 'auth']
