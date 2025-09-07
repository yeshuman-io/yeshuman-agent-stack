"""
MCP API endpoints using Django Ninja.
"""
from ninja import NinjaAPI, Schema
from .server import mcp_server, MCPRequest
from django.http import StreamingHttpResponse
from utils.sse import SSEHttpResponse
import json
import sys

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
                "protocolVersion": "2025-06-18",  # Match Claude Desktop's version
                "capabilities": {
                    "tools": {
                        "listChanged": True
                    },
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


@mcp_api.api_operation(["GET", "POST"], "/")
async def mcp_endpoint(request):
    """Main MCP endpoint with streaming response for MCP protocol."""
    import logging
    logger = logging.getLogger(__name__)

    # Log the incoming request immediately
    logger.info("🔗 MCP endpoint called")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   Path: {request.path}")
    logger.info(f"   Headers: {dict(request.headers)}")

    print(f"🔗 MCP endpoint called: {request.method} {request.path}", file=sys.stderr)
    print(f"   User-Agent: {request.headers.get('User-Agent', 'Unknown')}", file=sys.stderr)

    try:
        # Enhanced request logging for debugging
        logger.info(f"MCP Request: {request.method} {request.path}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")

        # Handle GET requests (MCP protocol negotiation)
        if request.method == "GET":
            print("📡 Handling GET request - MCP protocol negotiation", file=sys.stderr)
            logger.info("Handling GET request - MCP protocol negotiation")
            try:
                init_request = MCPRequest(method="initialize", id="init")
                print("🚀 Sending initialize request to server", file=sys.stderr)
                init_response = await mcp_server.handle_request(init_request)
                logger.info(f"GET Response: {init_response.dict()}")
                print(f"✅ GET response generated: {init_response.dict()}", file=sys.stderr)
                return init_response.dict()
            except Exception as e:
                logger.error(f"❌ Error during GET initialization: {str(e)}", exc_info=True)
                print(f"❌ Error during GET initialization: {str(e)}", file=sys.stderr)
                return {"error": f"Server initialization failed: {str(e)}"}

        # Parse the JSON-RPC request for POST
        print("📨 Handling POST request - parsing JSON-RPC", file=sys.stderr)
        print(f"📦 Raw request body: {request.body}", file=sys.stderr)

        if not request.body:
            print("⚠️ Empty request body", file=sys.stderr)
            return StreamingHttpResponse(
                [json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Empty request body"},
                    "id": None
                })],
                content_type='application/json'
            )

        body = json.loads(request.body)
        logger.info(f"Request body: {body}")
        print(f"📋 Parsed request body: {body}", file=sys.stderr)

        # Handle Cursor's stdio-style initialization if no body
        if not body or not body.get("method"):
            print("⚠️ Empty/malformed body - sending initialization response", file=sys.stderr)
            logger.warning("Received POST with empty/malformed body - sending initialization response")
            init_request = MCPRequest(method="initialize", id="init")
            init_response = await mcp_server.handle_request(init_request)
            logger.info(f"Empty body response: {init_response.dict()}")
            print(f"📤 Empty body response: {init_response.dict()}", file=sys.stderr)
            return init_response.dict()

        # Create MCPRequest from raw data
        mcp_request = MCPRequest(
            method=body.get("method", ""),
            params=body.get("params", {}),
            id=body.get("id")
        )

        logger.info(f"Processing MCP request: method={mcp_request.method}, id={mcp_request.id}")

        # Track timing for performance monitoring
        import time
        start_time = time.time()

        response = await mcp_server.handle_request(mcp_request)

        processing_time = time.time() - start_time
        logger.info(".2f")

        # Return as streaming response for MCP compatibility
        print(f"🎯 Processing MCP request: {mcp_request.method} id={mcp_request.id}", file=sys.stderr)
        print(f"⏱️ Starting request processing", file=sys.stderr)

        response = await mcp_server.handle_request(mcp_request)

        processing_time = time.time() - start_time
        logger.info(".2f")
        print(".2f", file=sys.stderr)

        def generate_response():
            response_dict = response.dict(exclude_none=True)
            logger.info(f"Final response: {response_dict}")
            print(f"📤 Generated response: {response_dict}", file=sys.stderr)
            yield json.dumps(response_dict)

        print("🌊 Creating streaming response", file=sys.stderr)
        streaming_response = StreamingHttpResponse(
            generate_response(),
            content_type='application/json'
        )
        print("✅ Streaming response created", file=sys.stderr)
        return streaming_response
        
    except json.JSONDecodeError as e:
        print(f"❌ JSONDecodeError: {str(e)}", file=sys.stderr)
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
        print(f"💥 Exception in MCP endpoint: {str(e)}", file=sys.stderr)
        import traceback
        print(f"Stack trace: {traceback.format_exc()}", file=sys.stderr)
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
    print("🛠️ Tools endpoint called", file=sys.stderr)
    tools = mcp_server.list_tools()
    print(f"📋 Returning tools: {tools}", file=sys.stderr)
    return tools


@mcp_api.get("/test")
def test_endpoint(request):
    """Test endpoint to verify MCP server is working."""
    print("🧪 Test endpoint called", file=sys.stderr)
    return {
        "status": "ok",
        "message": "MCP server is working",
        "tools_count": len(mcp_server.list_tools().get("tools", []))
    }


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
