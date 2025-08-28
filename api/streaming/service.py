"""
Universal streaming service for multi-consumer protocol support.

This service provides a unified interface for streaming LangGraph outputs
to different consumer formats (Anthropic, MCP, A2A).
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, Literal
from agent.graph import astream_agent
from .generators import AnthropicSSEGenerator

logger = logging.getLogger(__name__)


class MCPStreamingHandler:
    """Handler for MCP JSON-RPC streaming format."""
    
    async def format_event(self, event: Dict[str, Any]) -> bytes:
        """Convert LangGraph event to MCP JSON-RPC format."""
        content = event.get("content", "")
        if not content:
            return b""
            
        mcp_response = {
            "jsonrpc": "2.0",
            "result": {
                "role": "assistant",
                "parts": [{"type": "text/plain", "data": content}]
            }
        }
        return f"data: {json.dumps(mcp_response)}\n\n".encode('utf-8')


class A2AStreamingHandler:
    """Handler for A2A protocol streaming format."""
    
    async def format_event(self, event: Dict[str, Any]) -> bytes:
        """Convert LangGraph event to A2A protocol format."""
        content = event.get("content", "")
        if not content:
            return b""
            
        a2a_response = {
            "role": "assistant", 
            "parts": [{"type": "text/plain", "data": content}]
        }
        return f"data: {json.dumps(a2a_response)}\n\n".encode('utf-8')


class UniversalStreamingService:
    """
    Universal streaming service that adapts LangGraph outputs
    to different consumer protocols.
    """
    
    def __init__(self, protocol: Literal["anthropic", "mcp", "a2a"]):
        """
        Initialize the streaming service with a specific protocol.
        
        Args:
            protocol: The target protocol format ("anthropic", "mcp", "a2a")
        """
        self.protocol = protocol
        
        if protocol == "anthropic":
            self.handler = AnthropicSSEGenerator()
        elif protocol == "mcp":
            self.handler = MCPStreamingHandler()
        elif protocol == "a2a":
            self.handler = A2AStreamingHandler()
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
    
    async def stream_agent_response(self, message: str) -> AsyncGenerator[bytes, None]:
        """
        Stream agent response in the configured protocol format.
        
        Args:
            message: The user message to process
            
        Yields:
            Bytes formatted according to the configured protocol
        """
        try:
            if self.protocol == "anthropic":
                # Use the sophisticated SSE generator for Anthropic format
                # Create a simple stream from the current agent
                async def simple_stream_generator():
                    async for token in astream_agent(message):
                        yield {"type": "message", "content": token}
                
                # Transform through Anthropic SSE generator
                async for event in self.handler.generate_sse(simple_stream_generator()):
                    yield event
                    
            else:
                # Use simpler formatters for MCP/A2A
                async for token in astream_agent(message):
                    # Create a simple event structure
                    event = {"type": "message", "content": token}
                    formatted = await self.handler.format_event(event)
                    if formatted:
                        yield formatted
                        
        except Exception as e:
            logger.error(f"Error in universal streaming service: {str(e)}")
            # Send error in appropriate format
            if self.protocol == "anthropic":
                error_event = f"event: error\ndata: {{\"type\": \"error\", \"error\": {{\"message\": \"{str(e)}\"}}}}\n\n"
                yield error_event.encode('utf-8')
            else:
                error_response = {"error": str(e)}
                yield f"data: {json.dumps(error_response)}\n\n".encode('utf-8')

