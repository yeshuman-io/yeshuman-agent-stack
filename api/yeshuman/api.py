"""
Main API routes using Django Ninja.
"""
import os
from ninja import NinjaAPI, Schema
from typing import Dict, Any, Optional
from agent.graph import ainvoke_agent, create_agent

# Initialize the API
api = NinjaAPI(
    title="YesHuman Agent API",
    version="1.0.0",
    description="API for YesHuman Agent Stack with MCP and A2A support"
)


# Schemas
class ChatRequest(Schema):
    message: str
    session_id: Optional[str] = None


class ChatResponse(Schema):
    success: bool
    response: str
    session_id: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(Schema):
    status: str
    version: str
    agent_ready: bool


class A2ARequest(Schema):
    agent_id: str
    message: str
    context: Optional[Dict[str, Any]] = {}


class A2AResponse(Schema):
    success: bool
    response: str
    agent_id: str
    error: Optional[str] = None


# Health check endpoint
@api.get("/health", response=HealthResponse)
def health_check(request):
    """Health check endpoint."""
    agent_ready = True
    try:
        # Test if we can create the agent
        create_agent()
    except Exception:
        agent_ready = False
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agent_ready": agent_ready
    }


# Chat endpoint
@api.post("/chat", response=ChatResponse)
async def chat(request, payload: ChatRequest):
    """Chat with the YesHuman agent."""
    try:
        result = await ainvoke_agent(payload.message)
        
        return ChatResponse(
            success=result["success"],
            response=result["response"],
            session_id=payload.session_id,
            error=result.get("error")
        )
    except Exception as e:
        return ChatResponse(
            success=False,
            response="Sorry, I encountered an error processing your request.",
            session_id=payload.session_id,
            error=str(e)
        )


# MCP endpoints are handled by the dedicated MCP API at /mcp/
# See mcp/api.py for full MCP protocol implementation


# A2A endpoints are handled by the dedicated A2A API at /a2a/
# See a2a/api.py for full Agent-to-Agent protocol implementation
# This endpoint remains for simple A2A message integration with the main agent

@api.post("/a2a/simple", response=A2AResponse)
async def simple_a2a_handler(request, payload: A2ARequest):
    """Simple A2A message handler that integrates with the main agent."""
    try:
        # Format message with agent context
        formatted_message = f"Message from agent '{payload.agent_id}': {payload.message}"
        if payload.context:
            formatted_message += f"\nContext: {payload.context}"
        
        result = await ainvoke_agent(formatted_message)
        
        return A2AResponse(
            success=result["success"],
            response=result["response"],
            agent_id=payload.agent_id,
            error=result.get("error")
        )
    
    except Exception as e:
        return A2AResponse(
            success=False,
            response="Error processing A2A request",
            agent_id=payload.agent_id,
            error=str(e)
        )


# Test endpoint for development
@api.get("/test")
async def test_agent(request):
    """Test endpoint to verify agent functionality."""
    try:
        result = await ainvoke_agent("Hello! Can you calculate 2 + 2 for me?")
        return {"test_result": result}
    except Exception as e:
        return {"error": str(e)}
