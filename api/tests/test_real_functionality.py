"""
Tests for real functionality - no mocking, just testing what actually works.
"""
import os
import pytest
from django.test import TestCase, Client
from agent.graph import create_agent, astream_agent


class TestRealFunctionality(TestCase):
    """Test real functionality without mocking."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_agent_card_a2a_real_response(self):
        """Test that A2A agent card returns real, valid data."""
        response = self.client.get('/a2a/agent-card/a2a')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Test real data structure (no mocking)
        self.assertEqual(data["name"], "YesHuman Agent")
        self.assertIn("streaming", data["capabilities"])
        self.assertTrue(data["capabilities"]["streaming"])
        self.assertEqual(data["preferredTransport"], "JSONRPC")
        
        # Should have real skills
        self.assertGreater(len(data["skills"]), 0)
        
        # Each skill should have required fields
        for skill in data["skills"]:
            self.assertIn("id", skill)
            self.assertIn("name", skill)
            self.assertIn("description", skill)
    
    @pytest.mark.asyncio
    async def test_async_streaming_real_behavior(self):
        """Test async streaming with real agent behavior."""
        events = []
        
        # Test real streaming
        async for event in astream_agent("Say hello world"):
            events.append(event)
            if len(events) >= 3:  # Limit for test speed
                break
        
        # Should capture real events
        self.assertGreater(len(events), 0)
        # Each event should be a dict with type
        for event in events:
            self.assertIsInstance(event, dict)
            self.assertIn('type', event)
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
    def test_agent_creation_real(self):
        """Test real agent creation (requires API key)."""
        # Test agent creation (async-only now)
        agent = create_agent()
        self.assertIsNotNone(agent)
        
        # Verify it has async methods
        self.assertTrue(hasattr(agent, 'ainvoke'))
        self.assertTrue(hasattr(agent, 'astream'))
    
    def test_a2a_jsonrpc_endpoint_structure(self):
        """Test A2A JSON-RPC endpoint returns proper structure (without mocking)."""
        # Test with simple message using real auth
        response = self.client.post(
            '/a2a/',
            data='{"jsonrpc": "2.0", "id": "test", "method": "message/send", "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": "hello"}]}}}',
            content_type='application/json',
            HTTP_X_API_KEY='test-key-789'  # Use test key from .env
        )
        
        # Should return valid JSON-RPC structure (real response)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check real JSON-RPC structure
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertIn("result", data)
        
        # Check real message structure
        result = data["result"]
        self.assertIn("messageId", result)
        self.assertEqual(result["role"], "agent")
        self.assertIn("parts", result)
    
    def test_streaming_endpoint_real_structure(self):
        """Test streaming endpoint returns real SSE structure."""
        payload = '{"jsonrpc": "2.0", "id": "stream-test", "method": "message/stream", "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": "hi"}]}}}'
        
        response = self.client.post(
            '/a2a/',
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='text/event-stream',
            HTTP_X_API_KEY='test-key-789'  # Use test key from .env
        )
        
        # Should return real streaming response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        
        # Should have real SSE content
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('data:', content)
        
        # Content should have real structure (not empty)
        self.assertGreater(len(content.strip()), 0)


class TestRealIntegration:
    """Test real integration scenarios (no Django TestCase for async)."""
    
    def test_available_tools_are_real(self):
        """Test that available tools are real and functional."""
        from tools.utilities import AVAILABLE_TOOLS
        
        # Should have real tools
        assert len(AVAILABLE_TOOLS) > 0
        
        tool_names = [tool.name for tool in AVAILABLE_TOOLS]
        
        # Should have expected real tools
        expected_tools = ["calculator", "echo", "weather", "text_analysis", "agent_chat", "agent_capabilities"]
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Missing expected tool: {tool_name}"
    
    @pytest.mark.asyncio
    async def test_calculator_tool_real_functionality(self):
        """Test calculator tool with real calculations."""
        from tools.utilities import AVAILABLE_TOOLS
        
        calc_tool = next(tool for tool in AVAILABLE_TOOLS if tool.name == "calculator")
        
        # Test real calculations
        result = await calc_tool._arun("2 + 2")
        assert "4" in result
        
        result = await calc_tool._arun("10 * 5")
        assert "50" in result
    
    @pytest.mark.asyncio
    async def test_echo_tool_real_functionality(self):
        """Test echo tool with real echoing."""
        from tools.utilities import AVAILABLE_TOOLS
        
        echo_tool = next(tool for tool in AVAILABLE_TOOLS if tool.name == "echo")
        
        # Test real echo
        result = await echo_tool._arun("test message")
        assert result == "Echo: test message"
        
        result = await echo_tool._arun("hello world")
        assert result == "Echo: hello world"


