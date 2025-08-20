"""
Integration tests for MCP SSE endpoints.
Following testing rule: no mocking, test actual system behavior.
"""
import os
import django
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
import json

if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yeshuman.settings')
    django.setup()


class TestMCPSSE(TestCase):
    """Test MCP SSE functionality with real tools."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def _get_sse_events(self, response):
        """Parse SSE events from response."""
        content = b''.join(response.streaming_content).decode('utf-8')
        events = []
        for line in content.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
        return events
    
    def test_mcp_sse_endpoint_initialization(self):
        """Test SSE endpoint returns proper MCP initialization."""
        response = self.client.get('/mcp/sse')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        
        events = self._get_sse_events(response)
        self.assertGreaterEqual(len(events), 2)  # Init and tools list
        
        # First event should be initialization
        init_event = events[0]
        self.assertEqual(init_event['id'], 'init')
        self.assertIn('protocolVersion', init_event['result'])
        
        # Second event should be tools list
        tools_event = events[1]
        self.assertEqual(tools_event['id'], 'tools')
        self.assertIn('tools', tools_event['result'])
    
    def test_mcp_sse_call_tool(self):
        """Test SSE endpoint can call tools."""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "calculator",
                "arguments": {"expression": "10 + 5"}
            },
            "id": "sse-calc-test"
        }
        
        response = self.client.post(
            '/mcp/sse',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        
        events = self._get_sse_events(response)
        self.assertGreaterEqual(len(events), 3)  # Init, tools, and result
        
        # Last event should be the tool result
        result_event = events[-1]
        self.assertEqual(result_event['id'], 'sse-calc-test')
        self.assertIn('result', result_event)
        self.assertIn('15', result_event['result']['content'][0]['text'])
    
    def test_tools_sse_endpoint(self):
        """Test dedicated tools SSE endpoint."""
        response = self.client.get('/mcp/tools/sse')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        
        # Get the streaming content
        content = b''.join(response.streaming_content).decode('utf-8')
        
        # Should contain tools data
        self.assertIn('calculator', content)
        self.assertIn('echo', content)