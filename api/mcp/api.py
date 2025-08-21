"""
MCP API endpoints using Django Ninja.
"""
from ninja import NinjaAPI, Schema
from .server import mcp_server, MCPRequest, MCPResponse
from .sse import sse_mcp_endpoint, mcp_tools_sse

# Create MCP API instance
mcp_api = NinjaAPI(
    title="YesHuman MCP Server",
    version="1.0.0",
    description="Model Context Protocol server for YesHuman tools",
    urls_namespace="mcp"
)


from django.http import StreamingHttpResponse
import json


@mcp_api.post("/")
def mcp_endpoint(request):
    """Main MCP endpoint with streaming response for MCP protocol."""
    try:
        # Parse the JSON-RPC request
        body = json.loads(request.body)
        
        # Create MCPRequest from raw data
        mcp_request = MCPRequest(
            method=body.get("method", ""),
            params=body.get("params", {}),
            id=body.get("id")
        )
        
        response = mcp_server.handle_request(mcp_request)
        
        # Return as streaming response for MCP compatibility
        def generate_response():
            # Convert to dict and exclude None values
            response_dict = response.dict(exclude_none=True)
            yield json.dumps(response_dict)
        
        return StreamingHttpResponse(
            generate_response(),
            content_type='application/json'
        )
        
    except json.JSONDecodeError:
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error"
            },
            "id": None
        }
        return StreamingHttpResponse(
            [json.dumps(error_response)],
            content_type='application/json'
        )
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": None
        }
        return StreamingHttpResponse(
            [json.dumps(error_response)],
            content_type='application/json'
        )


@mcp_api.get("/tools")
def list_tools_endpoint(request):
    """Convenience endpoint to list available tools."""
    return mcp_server.list_tools()


class ToolCallRequest(Schema):
    tool_name: str
    arguments: dict = {}


@mcp_api.post("/tools/call")
def call_tool_endpoint(request, payload: ToolCallRequest):
    """Convenience endpoint to call a tool directly."""
    try:
        result = mcp_server.call_tool(payload.tool_name, payload.arguments)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp_api.get("/sse")
def mcp_sse_endpoint(request):
    """SSE endpoint for MCP protocol - proper streaming connection."""
    return sse_mcp_endpoint(request)


@mcp_api.post("/sse")
def mcp_sse_post_endpoint(request):
    """SSE endpoint for MCP protocol - handle POST requests."""
    return sse_mcp_endpoint(request)


@mcp_api.get("/tools/sse")
def tools_sse_endpoint(request):
    """SSE endpoint for streaming tools list."""
    return mcp_tools_sse(request)
