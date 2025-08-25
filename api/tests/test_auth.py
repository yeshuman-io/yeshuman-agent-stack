"""
Tests for authentication system - testing real functionality without mocking.
"""
import os
from unittest.mock import patch
from django.test import TestCase, Client
from auth.middleware import SimpleAPIKeyAuth


class TestAuthentication(TestCase):
    """Test real authentication functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_api_key_parsing_real(self):
        """Test real API key parsing from environment."""
        # Test with real environment variables
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'inspector:dev-key-123,agent1:prod-key-456',
            'MCP_API_KEY': 'mcp-secret-789',
            'A2A_AUTH_ENABLED': 'True',
            'MCP_AUTH_ENABLED': 'False'
        }):
            auth = SimpleAPIKeyAuth()
            
            # Should parse A2A keys correctly
            self.assertEqual(len(auth.a2a_api_keys), 2)
            self.assertEqual(auth.a2a_api_keys['dev-key-123'], 'inspector')
            self.assertEqual(auth.a2a_api_keys['prod-key-456'], 'agent1')
            
            # Should parse MCP key correctly
            self.assertEqual(auth.mcp_api_key, 'mcp-secret-789')
            
            # Should parse flags correctly
            self.assertTrue(auth.a2a_auth_enabled)
            self.assertFalse(auth.mcp_auth_enabled)
    
    def test_a2a_auth_disabled_real(self):
        """Test A2A auth when disabled (real behavior)."""
        with patch.dict(os.environ, {'A2A_AUTH_ENABLED': 'False'}):
            auth = SimpleAPIKeyAuth()
            
            # Mock request without API key
            class MockRequest:
                headers = {}
            
            request = MockRequest()
            is_auth, error = auth.authenticate_a2a(request)
            
            # Should allow access when disabled
            self.assertTrue(is_auth)
            self.assertIsNone(error)
    
    def test_a2a_auth_enabled_valid_key_real(self):
        """Test A2A auth with valid key (real behavior)."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'test-client:test-key-123',
            'A2A_AUTH_ENABLED': 'True'
        }):
            auth = SimpleAPIKeyAuth()
            
            # Mock request with valid API key
            class MockRequest:
                headers = {'X-API-Key': 'test-key-123'}
            
            request = MockRequest()
            is_auth, error = auth.authenticate_a2a(request)
            
            # Should allow access with valid key
            self.assertTrue(is_auth)
            self.assertIsNone(error)
            self.assertEqual(request.authenticated_client, 'test-client')
    
    def test_a2a_auth_enabled_invalid_key_real(self):
        """Test A2A auth with invalid key (real behavior)."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'test-client:test-key-123',
            'A2A_AUTH_ENABLED': 'True'
        }):
            auth = SimpleAPIKeyAuth()
            
            # Mock request with invalid API key
            class MockRequest:
                headers = {'X-API-Key': 'wrong-key'}
            
            request = MockRequest()
            is_auth, error = auth.authenticate_a2a(request)
            
            # Should deny access with invalid key
            self.assertFalse(is_auth)
            self.assertEqual(error, "Invalid API key")
    
    def test_a2a_auth_enabled_missing_key_real(self):
        """Test A2A auth with missing key (real behavior)."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': 'test-client:test-key-123',
            'A2A_AUTH_ENABLED': 'True'
        }):
            auth = SimpleAPIKeyAuth()
            
            # Mock request without API key
            class MockRequest:
                headers = {}
            
            request = MockRequest()
            is_auth, error = auth.authenticate_a2a(request)
            
            # Should deny access without key
            self.assertFalse(is_auth)
            self.assertEqual(error, "Missing X-API-Key header")
    
    def test_mcp_auth_real(self):
        """Test MCP auth (real behavior)."""
        with patch.dict(os.environ, {
            'MCP_API_KEY': 'mcp-secret-789',
            'MCP_AUTH_ENABLED': 'True'
        }):
            auth = SimpleAPIKeyAuth()
            
            # Test valid key
            class MockRequestValid:
                headers = {'X-API-Key': 'mcp-secret-789'}
            
            request = MockRequestValid()
            is_auth, error = auth.authenticate_mcp(request)
            self.assertTrue(is_auth)
            self.assertIsNone(error)
            
            # Test invalid key
            class MockRequestInvalid:
                headers = {'X-API-Key': 'wrong-key'}
            
            request = MockRequestInvalid()
            is_auth, error = auth.authenticate_mcp(request)
            self.assertFalse(is_auth)
            self.assertEqual(error, "Invalid API key")
    
    def test_auth_error_response_real(self):
        """Test auth error response format (real behavior)."""
        auth = SimpleAPIKeyAuth()
        response = auth.create_auth_error_response("Test error message")
        
        # Should return proper JSON error
        self.assertEqual(response.status_code, 401)
        
        # Check response content
        import json
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['error'], 'Authentication failed')
        self.assertEqual(content['message'], 'Test error message')
    
    def test_empty_api_keys_real(self):
        """Test behavior with empty API keys (real edge case)."""
        with patch.dict(os.environ, {
            'A2A_API_KEYS': '',
            'MCP_API_KEY': '',
            'A2A_AUTH_ENABLED': 'True',
            'MCP_AUTH_ENABLED': 'True'
        }):
            auth = SimpleAPIKeyAuth()
            
            # Should handle empty keys gracefully
            self.assertEqual(len(auth.a2a_api_keys), 0)
            self.assertEqual(auth.mcp_api_key, '')
            
            # Any request should fail
            class MockRequest:
                headers = {'X-API-Key': 'any-key'}
            
            request = MockRequest()
            is_auth, error = auth.authenticate_a2a(request)
            self.assertFalse(is_auth)
            self.assertEqual(error, "Invalid API key")
