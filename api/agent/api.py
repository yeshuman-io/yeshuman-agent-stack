"""
Agent API endpoints for custom UI consumers.

This module provides a unified streaming endpoint that returns Anthropic-compatible
SSE streams for custom UIs expecting delta events. Follows the server/ pattern.
"""
import json
import logging
from ninja import NinjaAPI
from pydantic import BaseModel

from utils.sse import SSEHttpResponse
from streaming.generators import AnthropicSSEGenerator
from agent.graph import astream_agent_tokens

logger = logging.getLogger(__name__)

agent_api = NinjaAPI(urls_namespace="agent")


class AgentRequest(BaseModel):
    """Request model for agent interactions."""
    message: str


@agent_api.api_operation(["GET", "POST", "OPTIONS"], "/stream", summary="Unified Agent Streaming Endpoint")
async def stream(request):
    """
    Unified streaming endpoint following server/ pattern.
    
    Handles GET, POST, and OPTIONS requests:
    - OPTIONS /agent/stream           -> CORS preflight
    - GET  /agent/stream?init=welcome -> Initialization streams  
    - GET  /agent/stream?message=...  -> Direct message streams
    - POST /agent/stream             -> User message streams via JSON body
    
    Returns:
        SSEHttpResponse with Anthropic-compatible streaming events
    """
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        from django.http import HttpResponse
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        return response
    
    if request.method == "POST":
        # Handle POST request with JSON body
        try:
            data = json.loads(request.body)
            message = data.get("message", "")
            if not message:
                # Return error as SSE stream for consistency
                async def error_stream():
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Message is required in POST body'})}\n\n"
                response = SSEHttpResponse(error_stream())
                response["Access-Control-Allow-Origin"] = "*"
                return response
                
        except json.JSONDecodeError:
            # Return error as SSE stream for consistency  
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Invalid JSON in request body'})}\n\n"
            response = SSEHttpResponse(error_stream())
            response["Access-Control-Allow-Origin"] = "*"
            return response
            
    else:  # GET request
        # Handle GET request with query parameters
        message = request.GET.get('message')
        user_state = request.GET.get('user_state', 'new_user')
        
        if not message:
            # No hardcoded messages - return error if no message provided
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Message is required'})}\n\n"
            response = SSEHttpResponse(error_stream())
            response["Access-Control-Allow-Origin"] = "*"
            return response
    
    # Stream the agent response using AnthropicSSEGenerator
    try:
        sse_generator = AnthropicSSEGenerator()
        response = SSEHttpResponse(sse_generator.generate_sse(astream_agent_tokens(message)))
        # Add CORS headers
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        return response
        
    except Exception as e:
        logger.error(f"Agent streaming error: {str(e)}")
        # Return error as SSE stream for consistency
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Agent execution encountered an error'})}\n\n"
        response = SSEHttpResponse(error_stream())
        response["Access-Control-Allow-Origin"] = "*"
        return response