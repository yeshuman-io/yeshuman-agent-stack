"""
Tests for Django authentication backend - testing real functionality without mocking.
"""
import os
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from auth.backends import UniversalAPIKeyBackend, APIKeyUser


class TestDjangoAuthentication(TestCase):
    """Test Django authentication backend functionality."""
    
    def setUp(self):
        """Set up test components."""
        self.factory = RequestFactory()
        self.backend = UniversalAPIKeyBackend()
    
    def test_backend_authentication_a2a(self):
        """Test backend authentication for A2A keys."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'inspector:dev-key-123,agent1:prod-key-456',
            'A2A_AUTH_ENABLED': 'True'
        }):
            # Re-initialize backend with new environment
            backend = UniversalAPIKeyBackend()
            
            # Create request with valid A2A key
            request = self.factory.get('/test/')
            request.META['HTTP_X_API_KEY'] = 'dev-key-123'
            
            user = backend.authenticate(request)
            
            # Should return APIKeyUser
            self.assertIsInstance(user, APIKeyUser)
            self.assertEqual(user.client_name, 'inspector')
            self.assertEqual(user.api_key_type, 'a2a')
            self.assertTrue(user.is_authenticated)
    
    def test_backend_authentication_mcp(self):
        """Test backend authentication for MCP keys."""
        with patch.dict(os.environ, {
            'MCP_API_KEY': 'mcp-secret-789',
            'MCP_AUTH_ENABLED': 'True'
        }):
            # Re-initialize backend with new environment
            backend = UniversalAPIKeyBackend()
            
            # Create request with valid MCP key
            request = self.factory.get('/test/')
            request.META['HTTP_X_API_KEY'] = 'mcp-secret-789'
            
            user = backend.authenticate(request)
            
            # Should return APIKeyUser
            self.assertIsInstance(user, APIKeyUser)
            self.assertEqual(user.client_name, 'mcp_client')
            self.assertEqual(user.api_key_type, 'mcp')
            self.assertTrue(user.is_authenticated)
    
    def test_backend_authentication_invalid_key(self):
        """Test backend authentication with invalid key."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'inspector:dev-key-123',
            'A2A_AUTH_ENABLED': 'True'
        }):
            # Re-initialize backend with new environment
            backend = UniversalAPIKeyBackend()
            
            # Create request with invalid key
            request = self.factory.get('/test/')
            request.META['HTTP_X_API_KEY'] = 'wrong-key'
            
            user = backend.authenticate(request)
            
            # Should return None for invalid key
            self.assertIsNone(user)
    
    def test_backend_authentication_no_key(self):
        """Test backend authentication without API key header."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'inspector:dev-key-123',
            'A2A_AUTH_ENABLED': 'True'
        }):
            # Re-initialize backend with new environment
            backend = UniversalAPIKeyBackend()
            
            # Create request without API key
            request = self.factory.get('/test/')
            
            user = backend.authenticate(request)
            
            # Should return None when no key provided
            self.assertIsNone(user)
    
    def test_backend_auth_disabled(self):
        """Test backend when authentication is disabled."""
        with patch.dict(os.environ, {
            'A2A_AUTH_ENABLED': 'False',
            'MCP_AUTH_ENABLED': 'False'
        }):
            # Re-initialize backend with new environment
            backend = UniversalAPIKeyBackend()
            
            # Create request with API key but auth disabled
            request = self.factory.get('/test/')
            request.META['HTTP_X_API_KEY'] = 'any-key'
            
            user = backend.authenticate(request)
            
            # Should return None when auth is disabled
            self.assertIsNone(user)


class TestAPIKeyUser(TestCase):
    """Test APIKeyUser model functionality."""
    
    def test_api_key_user_properties(self):
        """Test APIKeyUser properties."""
        user = APIKeyUser('test_client', 'a2a')
        
        self.assertEqual(user.client_name, 'test_client')
        self.assertEqual(user.api_key_type, 'a2a')
        self.assertTrue(user.is_authenticated)
        self.assertFalse(user.is_anonymous)
        self.assertIsNone(user.pk)
        self.assertEqual(str(user), 'APIKeyUser(test_client, a2a)')