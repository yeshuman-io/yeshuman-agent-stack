"""
Agent API endpoints for custom UI consumers.

This module provides endpoints that return Anthropic-compatible
SSE streams for custom UIs expecting delta events.
"""
import json
import logging
from ninja import NinjaAPI
from pydantic import BaseModel
from django.http import HttpResponse
from utils.sse import SSEHttpResponse
from streaming.generators import AnthropicSSEGenerator
from agent.graph import astream_agent

logger = logging.getLogger(__name__)

agent_api = NinjaAPI(urls_namespace="agent")


class AgentRequest(BaseModel):
    """Request model for agent interactions."""
    message: str


class AgentResponse(BaseModel):
    """Response model for non-streaming agent interactions."""
    response: str
    success: bool


@agent_api.api_operation(["OPTIONS"], "/stream", summary="CORS preflight for agent stream")
def agent_stream_options(request):
    """Handle CORS preflight requests for the streaming endpoint."""
    response = HttpResponse()
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization, X-API-Key"
    response["Access-Control-Max-Age"] = "86400"
    return response


@agent_api.get("/stream", summary="Agent streaming (Anthropic SSE format) - GET")
async def agent_stream_get(request):
    """
    GET endpoint for agent streaming with init parameter support.
    
    Supports query parameters:
    - message: Direct message to send to agent
    - init: Initialization type (welcome, demo, test)
    
    Returns:
        SSEHttpResponse with Anthropic-compatible streaming events
    """
    message = request.GET.get('message')
    init_type = request.GET.get('init')
    
    if init_type:
        # Map init types to appropriate messages
        init_messages = {
            'welcome': 'Welcome! I\'m YesHuman, your AI assistant. How can I help you today?',
            'demo': 'This is a demonstration of thinking and response streaming.',
            'test': 'Testing the agent with thinking and response nodes.'
        }
        message = init_messages.get(init_type, f'Initializing with {init_type}...')
    elif not message:
        message = 'Hello! How can I help you today?'
    
    # Create a payload object
    class MockPayload:
        def __init__(self, message):
            self.message = message
    
    payload = MockPayload(message)
    return await agent_stream_post(request, payload)


@agent_api.post("/stream", summary="Agent streaming (Anthropic SSE format)")
async def agent_stream_post(request, payload: AgentRequest):
    """
    Streaming agent interaction using real LangGraph with SSEGenerator.
    
    Args:
        request: HTTP request object
        payload: The agent request containing the message
        
    Returns:
        SSEHttpResponse with Anthropic-compatible streaming events
    """
    
    # Use the existing SSEGenerator - agent emits correct format
    sse_generator = AnthropicSSEGenerator()
    return SSEHttpResponse(sse_generator.generate_sse(astream_agent(payload.message)))


@agent_api.post("/message", summary="Agent message interaction (non-streaming)")
async def agent_message_post(request, payload: AgentRequest):
    """
    Non-streaming agent message endpoint that delegates to the streaming endpoint.
    
    Args:
        request: HTTP request object
        payload: The agent request containing the message
        
    Returns:
        SSEHttpResponse with Anthropic-compatible streaming events
    """
    # Delegate to streaming endpoint
    return await agent_stream_post(request, payload)