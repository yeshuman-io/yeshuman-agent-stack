"""
Smoke tests for URL patterns - ensuring both trailing slash and no trailing slash work
"""
import pytest
from django.test import Client
from django.urls import reverse, NoReverseMatch


class TestURLPatterns:
    """Test that all URL patterns work with and without trailing slashes"""

    def setup_method(self):
        """Set up test client"""
        self.client = Client()

    def test_api_endpoints_flexible_slashes(self):
        """Test /api endpoints accept both trailing slash and no trailing slash"""
        # Test /api/health with both formats
        response_with_slash = self.client.get('/api/health/')
        response_without_slash = self.client.get('/api/health')

        # Both should return the same status (either 200 or whatever the actual status is)
        assert response_with_slash.status_code == response_without_slash.status_code

        # Test /api (root API endpoint)
        response_with_slash = self.client.get('/api/')
        response_without_slash = self.client.get('/api')

        assert response_with_slash.status_code == response_without_slash.status_code

    def test_mcp_endpoints_flexible_slashes(self):
        """Test /mcp endpoints accept both trailing slash and no trailing slash"""
        # Test GET requests
        response_with_slash = self.client.get('/mcp/')
        response_without_slash = self.client.get('/mcp')

        # Both should return the same status
        assert response_with_slash.status_code == response_without_slash.status_code

        # Test POST requests (MCP protocol)
        test_payload = {"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}

        response_with_slash = self.client.post(
            '/mcp/',
            data=test_payload,
            content_type='application/json'
        )
        response_without_slash = self.client.post(
            '/mcp',
            data=test_payload,
            content_type='application/json'
        )

        # Both should return the same status (not 500 due to redirect issues)
        assert response_with_slash.status_code == response_without_slash.status_code

    def test_a2a_endpoints_flexible_slashes(self):
        """Test /a2a endpoints accept both trailing slash and no trailing slash"""
        response_with_slash = self.client.get('/a2a/')
        response_without_slash = self.client.get('/a2a')

        assert response_with_slash.status_code == response_without_slash.status_code

    def test_agent_endpoints_flexible_slashes(self):
        """Test /agent endpoints accept both trailing slash and no trailing slash"""
        response_with_slash = self.client.get('/agent/')
        response_without_slash = self.client.get('/agent')

        assert response_with_slash.status_code == response_without_slash.status_code

    def test_auth_endpoints_flexible_slashes(self):
        """Test /auth endpoints accept both trailing slash and no trailing slash"""
        response_with_slash = self.client.get('/auth/')
        response_without_slash = self.client.get('/auth')

        assert response_with_slash.status_code == response_without_slash.status_code

    def test_admin_endpoints_removed(self):
        """Test /admin endpoints are removed (we don't use Django admin)"""
        response_without_slash = self.client.get('/admin')
        response_with_slash = self.client.get('/admin/')

        # Both should return 404 since we removed Django admin
        assert response_without_slash.status_code == 404
        assert response_with_slash.status_code == 404

    def test_no_double_slashes_allowed(self):
        """Test that double slashes don't cause issues"""
        # These should still work or return 404 (not crash)
        response = self.client.get('/api//health')  # Double slash
        assert response.status_code in [200, 404, 301, 302]  # Shouldn't crash

        response = self.client.get('/mcp//')  # Double slash
        assert response.status_code in [200, 404, 301, 302]  # Shouldn't crash

    def test_case_sensitivity(self):
        """Test that URLs are case sensitive as expected"""
        # These should return 404 (not crash)
        response = self.client.get('/API/health')
        assert response.status_code == 404

        response = self.client.get('/MCP')
        assert response.status_code == 404

    def test_mcp_sub_endpoints_flexible(self):
        """Test that MCP sub-endpoints also work with flexible slashes"""
        # Test /mcp/tools
        response_with_slash = self.client.get('/mcp/tools/')
        response_without_slash = self.client.get('/mcp/tools')

        # Should return same status (both 200, 404, or 405 depending on implementation)
        assert response_with_slash.status_code == response_without_slash.status_code

        # Test /mcp/sse
        response_with_slash = self.client.get('/mcp/sse/')
        response_without_slash = self.client.get('/mcp/sse')

        assert response_with_slash.status_code == response_without_slash.status_code

    def test_post_data_preservation(self):
        """Critical test: ensure POST data is preserved and no 500 errors from redirects"""
        test_payload = {"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}

        # Test /mcp POST without slash
        response = self.client.post(
            '/mcp',
            data=test_payload,
            content_type='application/json'
        )

        # Should NOT return 500 (internal server error from redirect)
        assert response.status_code != 500, "POST /mcp should not return 500 due to redirect issues"

        # Test /mcp POST with slash
        response = self.client.post(
            '/mcp/',
            data=test_payload,
            content_type='application/json'
        )

        # Should NOT return 500
        assert response.status_code != 500, "POST /mcp/ should not return 500 due to redirect issues"

    def test_all_endpoints_respond(self):
        """Test that all our main endpoints respond (not crash with 500)"""
        endpoints = [
            '/api',
            '/api/',
            '/mcp',
            '/mcp/',
            '/a2a',
            '/a2a/',
            '/agent',
            '/agent/',
            '/auth',
            '/auth/',
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code != 500, f"Endpoint {endpoint} should not return 500"
