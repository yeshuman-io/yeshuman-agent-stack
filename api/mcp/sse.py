"""
SSE-based MCP server implementation for proper MCP client compatibility.
"""
from django.http import StreamingHttpResponse
from utils.sse import SSEHttpResponse
from .server import mcp_server, MCPRequest
import json
import asyncio


def sse_mcp_endpoint(request):
    """SSE endpoint for MCP protocol compatibility."""
    
    def event_stream():
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
                
                response = mcp_server.handle_request(mcp_request)
                
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
