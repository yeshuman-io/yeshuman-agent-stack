"""
Integration tests for MCP server.
Following testing rule: no mocking, test actual system behavior.
"""
import json
from django.test import TestCase, Client


class TestMCPServer(TestCase):
    """Test MCP server functionality with real tools."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_mcp_list_tools_endpoint(self):
        """Test MCP tools/list method."""
        payload = {
            "method": "tools/list",
            "params": {},
            "id": "test-1"
        }
        
        response = self.client.post(
            '/mcp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Handle both streaming and regular responses
        if hasattr(response, 'streaming_content'):
            content = b''.join(response.streaming_content).decode('utf-8')
            data = json.loads(content)
        else:
            data = response.json()
        
        # Check MCP response structure
        self.assertIsNone(data.get('error'))
        self.assertIsNotNone(data.get('result'))
        self.assertEqual(data.get('id'), 'test-1')
        
        # Check tools are listed
        tools = data['result']['tools']
        self.assertGreater(len(tools), 0)
        
        # Verify specific tools exist
        tool_names = [tool['name'] for tool in tools]
        self.assertIn('calculator', tool_names)
        self.assertIn('echo', tool_names)
        
        # Check tool structure
        calc_tool = next(tool for tool in tools if tool['name'] == 'calculator')
        self.assertIn('description', calc_tool)
        self.assertIn('inputSchema', calc_tool)
    
    def test_mcp_call_calculator_tool(self):
        """Test calling calculator tool via MCP."""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "calculator",
                "arguments": {
                    "expression": "15 * 8"
                }
            },
            "id": "calc-test"
        }
        
        response = self.client.post(
            '/mcp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Handle both streaming and regular responses
        if hasattr(response, 'streaming_content'):
            content = b''.join(response.streaming_content).decode('utf-8')
            data = json.loads(content)
        else:
            data = response.json()
        
        # Check MCP response structure
        self.assertIsNone(data.get('error'))
        self.assertIsNotNone(data.get('result'))
        self.assertEqual(data.get('id'), 'calc-test')
        
        # Check calculation result
        content = data['result']['content']
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['type'], 'text')
        self.assertIn('120', content[0]['text'])  # 15 * 8 = 120
    
    def test_mcp_call_echo_tool(self):
        """Test calling echo tool via MCP."""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "message": "Hello MCP World!"
                }
            },
            "id": "echo-test"
        }
        
        response = self.client.post(
            '/mcp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Handle both streaming and regular responses
        if hasattr(response, 'streaming_content'):
            content = b''.join(response.streaming_content).decode('utf-8')
            data = json.loads(content)
        else:
            data = response.json()
        
        # Check MCP response structure
        self.assertIsNone(data.get('error'))
        self.assertIsNotNone(data.get('result'))
        self.assertEqual(data.get('id'), 'echo-test')
        
        # Check echo result
        content = data['result']['content']
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['type'], 'text')
        self.assertEqual(content[0]['text'], 'Echo: Hello MCP World!')
    
    def test_mcp_invalid_tool(self):
        """Test calling non-existent tool."""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            },
            "id": "error-test"
        }
        
        response = self.client.post(
            '/mcp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Handle both streaming and regular responses
        if hasattr(response, 'streaming_content'):
            content = b''.join(response.streaming_content).decode('utf-8')
            data = json.loads(content)
        else:
            data = response.json()
        
        # Check error response
        self.assertIsNotNone(data.get('error'))
        self.assertIsNone(data.get('result'))
        self.assertEqual(data.get('id'), 'error-test')
        self.assertIn('not found', data['error']['message'])
    
    def test_mcp_invalid_method(self):
        """Test calling invalid MCP method."""
        payload = {
            "method": "invalid/method",
            "params": {},
            "id": "invalid-test"
        }
        
        response = self.client.post(
            '/mcp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Handle both streaming and regular responses
        if hasattr(response, 'streaming_content'):
            content = b''.join(response.streaming_content).decode('utf-8')
            data = json.loads(content)
        else:
            data = response.json()
        
        # Check error response
        self.assertIsNotNone(data.get('error'))
        self.assertIsNone(data.get('result'))
        self.assertEqual(data.get('id'), 'invalid-test')
        self.assertEqual(data['error']['code'], -32601)  # Method not found
    
    def test_convenience_list_tools_endpoint(self):
        """Test the convenience /mcp/tools endpoint."""
        response = self.client.get('/mcp/tools')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('tools', data)
        self.assertGreater(len(data['tools']), 0)
        
        tool_names = [tool['name'] for tool in data['tools']]
        self.assertIn('calculator', tool_names)
        self.assertIn('echo', tool_names)
    
    def test_convenience_call_tool_endpoint(self):
        """Test the convenience /mcp/tools/call endpoint."""
        payload = {
            "tool_name": "calculator",
            "arguments": {"expression": "7 * 6"}
        }
        
        response = self.client.post(
            '/mcp/tools/call',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Handle both streaming and regular responses
        if hasattr(response, 'streaming_content'):
            content = b''.join(response.streaming_content).decode('utf-8')
            data = json.loads(content)
        else:
            data = response.json()
        
        # Debug: print the actual response if it fails
        if not data.get('success'):
            print(f"Error response: {data}")
        
        self.assertTrue(data['success'])
        self.assertIn('result', data)
        # Check that calculation was performed
        result_text = data['result']['content'][0]['text']
        self.assertIn('42', result_text)  # 7 * 6 = 42
