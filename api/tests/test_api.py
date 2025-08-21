"""
Tests for the Django Ninja API endpoints.
"""
import os
import django
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from unittest.mock import patch
import json

# Configure Django settings for tests
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yeshuman.settings')
    django.setup()


class TestAPI(TestCase):
    """Test API endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['version'], '1.0.0')
        self.assertIn('agent_ready', data)
    
    def test_chat_endpoint_structure(self):
        """Test chat endpoint returns proper structure."""
        payload = {"message": "Hello"}
        response = self.client.post(
            '/api/chat',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('response', data)
        self.assertIn('session_id', data)
    
    def test_simple_a2a_endpoint_structure(self):
        """Test simple A2A endpoint returns proper structure."""
        payload = {
            "agent_id": "test-agent",
            "message": "Hello from another agent"
        }
        response = self.client.post(
            '/api/a2a/simple',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('response', data)
        self.assertIn('agent_id', data)
        self.assertEqual(data['agent_id'], 'test-agent')
    
    def test_api_structure_documentation(self):
        """Test that API structure is properly documented."""
        # MCP endpoints are now at /mcp/ (handled by mcp/api.py)
        # A2A endpoints are now at /a2a/ (handled by a2a/api.py)
        # Main API focuses on direct agent interaction
        
        # Test main API still has essential endpoints
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get('/api/test')
        self.assertEqual(response.status_code, 200)
    
    def test_test_endpoint(self):
        """Test the test endpoint."""
        response = self.client.get('/api/test')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('test_result', data)
