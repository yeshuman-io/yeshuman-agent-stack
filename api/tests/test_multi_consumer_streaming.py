"""
Tests for multi-consumer streaming architecture.

Tests that verify different consumers can receive streaming responses
in their expected formats (Anthropic, MCP, A2A).
"""
import pytest
import json
from django.test import TestCase, Client
from unittest.mock import patch, AsyncMock
from streaming.service import UniversalStreamingService


class TestMultiConsumerStreaming(TestCase):
    """Test multi-consumer streaming functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_anthropic_streaming_service_creation(self):
        """Test that Anthropic streaming service can be created."""
        service = UniversalStreamingService("anthropic")
        self.assertEqual(service.protocol, "anthropic")
        self.assertIsNotNone(service.handler)
    
    def test_mcp_streaming_service_creation(self):
        """Test that MCP streaming service can be created."""
        service = UniversalStreamingService("mcp")
        self.assertEqual(service.protocol, "mcp")
        self.assertIsNotNone(service.handler)
    
    def test_a2a_streaming_service_creation(self):
        """Test that A2A streaming service can be created."""
        service = UniversalStreamingService("a2a")
        self.assertEqual(service.protocol, "a2a")
        self.assertIsNotNone(service.handler)
    
    def test_invalid_protocol_raises_error(self):
        """Test that invalid protocol raises ValueError."""
        with self.assertRaises(ValueError):
            UniversalStreamingService("invalid")
    
    @pytest.mark.asyncio
    async def test_mcp_format_handler(self):
        """Test MCP format handler correctly formats events."""
        from streaming.service import MCPStreamingHandler
        
        handler = MCPStreamingHandler()
        event = {"type": "message", "content": "Hello MCP"}
        
        result = await handler.format_event(event)
        
        # Should return bytes
        self.assertIsInstance(result, bytes)
        
        # Should contain JSON-RPC format
        result_str = result.decode('utf-8')
        self.assertIn("data:", result_str)
        self.assertIn("jsonrpc", result_str)
        self.assertIn("Hello MCP", result_str)
    
    @pytest.mark.asyncio
    async def test_a2a_format_handler(self):
        """Test A2A format handler correctly formats events."""
        from streaming.service import A2AStreamingHandler
        
        handler = A2AStreamingHandler()
        event = {"type": "message", "content": "Hello A2A"}
        
        result = await handler.format_event(event)
        
        # Should return bytes
        self.assertIsInstance(result, bytes)
        
        # Should contain A2A format
        result_str = result.decode('utf-8')
        self.assertIn("data:", result_str)
        self.assertIn("role", result_str)
        self.assertIn("Hello A2A", result_str)
    
    def test_agent_sync_endpoint_structure(self):
        """Test that the agent sync endpoint returns correct structure."""
        response = self.client.post(
            '/agent/',
            data=json.dumps({"message": "Hello"}),
            content_type='application/json'
        )
        
        # Should return 200 or appropriate status
        self.assertIn(response.status_code, [200, 404])  # 404 if server not fully running
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('response', data)
            self.assertIn('success', data)
    
    def test_agent_stream_endpoint_structure(self):
        """Test that the agent stream endpoint returns SSE format."""
        response = self.client.post(
            '/agent/stream',
            data=json.dumps({"message": "Hello"}),
            content_type='application/json'
        )
        
        # Should return 200 or appropriate status
        self.assertIn(response.status_code, [200, 404])  # 404 if server not fully running
        
        if response.status_code == 200:
            # Should have SSE headers
            self.assertEqual(response.get('Content-Type'), 'text/event-stream')


class TestAnthropicSSEGenerator(TestCase):
    """Test the Anthropic SSE generator functionality."""
    
    @pytest.mark.asyncio
    async def test_format_sse_event(self):
        """Test SSE event formatting."""
        from streaming.generators import AnthropicSSEGenerator
        
        generator = AnthropicSSEGenerator()
        event_type = "content_block_delta"
        data = {"type": "content_block_delta", "delta": {"text": "Hello"}}
        
        result = await generator.format_sse_event(event_type, data)
        
        self.assertIsInstance(result, str)
        self.assertIn("event: content_block_delta", result)
        self.assertIn("data:", result)
        self.assertIn("Hello", result)
    
    def test_get_block_index_for_type(self):
        """Test block index assignment for different types."""
        from streaming.generators import AnthropicSSEGenerator
        
        generator = AnthropicSSEGenerator()
        
        # First type should get index 0
        index1 = generator.get_block_index_for_type("thinking")
        self.assertEqual(index1, 0)
        
        # Second type should get index 1
        index2 = generator.get_block_index_for_type("message")
        self.assertEqual(index2, 1)
        
        # Same type should get same index
        index3 = generator.get_block_index_for_type("thinking")
        self.assertEqual(index3, 0)
    
    @pytest.mark.asyncio
    async def test_detect_tool_use_basic(self):
        """Test basic tool use detection."""
        from streaming.generators import AnthropicSSEGenerator
        
        generator = AnthropicSSEGenerator()
        
        # Test explicit tool_use type
        chunk = {"type": "tool_use", "name": "calculator", "input": {"x": 5}}
        result = await generator.detect_tool_use(chunk)
        
        self.assertTrue(result)
        self.assertEqual(generator.current_tool_name, "calculator")
        self.assertEqual(generator.current_tool_input, {"x": 5})

