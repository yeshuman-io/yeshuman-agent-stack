"""
MCP API endpoints using Django Ninja.
"""
from ninja import NinjaAPI, Schema
from .server import mcp_server, MCPRequest
from django.http import StreamingHttpResponse
from utils.sse import SSEHttpResponse
import json

# Create MCP API instance
mcp_api = NinjaAPI(
    title="Yes Human MCP Server",
    version="1.0.0",
    description="Model Context Protocol server for Yes Human tools",
    urls_namespace="mcp"
)


# SSE Functions (merged from sse.py)
def sse_mcp_endpoint(request):
    """SSE endpoint for MCP protocol compatibility."""
    
    async def event_stream():
        """Generate SSE events for MCP communication."""
        # MCP initialization response
        init_response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "yeshuman-mcp-server",
                    "version": "1.0.0"
                }
            },
            "id": "init"
        }
        
        # Send initialization
        yield f"data: {json.dumps(init_response)}\n\n"
        
        # Send tools list immediately
        tools_response = {
            "jsonrpc": "2.0",
            "result": mcp_server.list_tools(),
            "id": "tools"
        }
        yield f"data: {json.dumps(tools_response)}\n\n"
        
        # Handle incoming requests
        if request.method == 'POST':
            try:
                body = json.loads(request.body)
                mcp_request = MCPRequest(
                    method=body.get("method", ""),
                    params=body.get("params", {}),
                    id=body.get("id")
                )
                
                response = await mcp_server.handle_request(mcp_request)
                
                # Format as JSON-RPC response
                jsonrpc_response = {
                    "jsonrpc": "2.0",
                    "result": response.result if response.result else None,
                    "error": response.error if response.error else None,
                    "id": response.id
                }
                
                yield f"data: {json.dumps(jsonrpc_response)}\n\n"
                
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": None
                }
                yield f"data: {json.dumps(error_response)}\n\n"
    
    return SSEHttpResponse(event_stream())


def mcp_tools_sse(request):
    """SSE endpoint that streams available tools."""
    
    def tools_stream():
        tools_data = mcp_server.list_tools()
        yield "event: tools\n"
        yield f"data: {json.dumps(tools_data)}\n\n"
    
    return SSEHttpResponse(tools_stream())


@mcp_api.post("/")
async def mcp_endpoint(request):
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
        
        response = await mcp_server.handle_request(mcp_request)
        
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
async def call_tool_endpoint(request, payload: ToolCallRequest):
    """Convenience endpoint to call a tool directly."""
    try:
        result = await mcp_server.call_tool(payload.tool_name, payload.arguments)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp_api.get("/sse")
def mcp_sse_endpoint_get(request):
    """SSE endpoint for MCP protocol - proper streaming connection."""
    return sse_mcp_endpoint(request)


@mcp_api.post("/sse")
def mcp_sse_endpoint_post(request):
    """SSE endpoint for MCP protocol - handle POST requests."""
    return sse_mcp_endpoint(request)


@mcp_api.get("/tools/sse")
def tools_sse_endpoint(request):
    """SSE endpoint for streaming tools list."""
    return mcp_tools_sse(request)
