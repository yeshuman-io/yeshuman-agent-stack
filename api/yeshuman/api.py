"""
Main API routes using Django Ninja.
"""
import os
from ninja import NinjaAPI, Schema
from typing import Dict, Any, Optional
from agents.agent import invoke_agent, create_agent

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


class MCPRequest(Schema):
    method: str
    params: Dict[str, Any] = {}


class MCPResponse(Schema):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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
def chat(request, payload: ChatRequest):
    """Chat with the YesHuman agent."""
    try:
        result = invoke_agent(payload.message)
        
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


# MCP Server endpoints
@api.post("/mcp", response=MCPResponse)
def mcp_handler(request, payload: MCPRequest):
    """Handle MCP (Model Context Protocol) requests."""
    try:
        # **Question: What specific MCP methods do you want to support?**
        # Common ones: list_tools, call_tool, list_resources, read_resource
        
        method = payload.method
        params = payload.params
        
        if method == "list_tools":
            # Return available tools
            from tools.utilities import AVAILABLE_TOOLS
            tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "schema": tool.args_schema.model_json_schema() if tool.args_schema else {}
                }
                for tool in AVAILABLE_TOOLS
            ]
            return MCPResponse(success=True, result={"tools": tools})
        
        elif method == "call_tool":
            # Call a specific tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            from tools.utilities import AVAILABLE_TOOLS
            tool = next((t for t in AVAILABLE_TOOLS if t.name == tool_name), None)
            
            if not tool:
                return MCPResponse(success=False, error=f"Tool '{tool_name}' not found")
            
            result = tool.run(tool_args)
            return MCPResponse(success=True, result={"output": result})
        
        else:
            return MCPResponse(success=False, error=f"Unsupported method: {method}")
    
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


# A2A (Agent-to-Agent) endpoints
@api.post("/a2a", response=A2AResponse)
def a2a_handler(request, payload: A2ARequest):
    """Handle Agent-to-Agent communication."""
    try:
        # **Question: What A2A patterns do you want to support?**
        # - Direct message passing?
        # - Task delegation?
        # - Resource sharing?
        
        # Format message with agent context
        formatted_message = f"Message from agent '{payload.agent_id}': {payload.message}"
        if payload.context:
            formatted_message += f"\nContext: {payload.context}"
        
        result = invoke_agent(formatted_message)
        
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
def test_agent(request):
    """Test endpoint to verify agent functionality."""
    try:
        result = invoke_agent("Hello! Can you calculate 2 + 2 for me?")
        return {"test_result": result}
    except Exception as e:
        return {"error": str(e)}
