"""
MCP Server implementation using Django Ninja and BaseTool tools.
"""
from ninja import NinjaAPI, Schema
from typing import Dict, Any, List, Optional, Union
from tools.utilities import MCP_TOOLS
from langchain_core.tools import BaseTool
import json

class MCPRequest(Schema):
    """Base MCP request schema."""
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[Union[str, int]] = None


class MCPResponse(Schema):
    """Base MCP response schema."""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class MCPServer:
    """MCP Server that exposes BaseTool tools via MCP protocol."""
    
    def __init__(self, tools: List[BaseTool]):
        import logging
        self.logger = logging.getLogger(__name__)
        self.tools = {tool.name: tool for tool in tools}

        # Log server initialization
        self.logger.info(f"MCP Server initialized with {len(self.tools)} tools: {list(self.tools.keys())}")

        # Log tool details
        for tool in tools:
            self.logger.info(f"Tool registered: {tool.name} - {tool.description}")
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schema_info = tool.args_schema.model_json_schema()
                self.logger.info(f"Tool {tool.name} schema: {schema_info}")
    
    def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        self.logger.info("Listing available tools")
        tools_list = []

        for tool in self.tools.values():
            self.logger.debug(f"Processing tool: {tool.name}")
            tool_info = {
                "name": tool.name,
                "description": tool.description,
            }

            # Add schema if available
            if hasattr(tool, 'args_schema') and tool.args_schema:
                tool_info["inputSchema"] = tool.args_schema.model_json_schema()
                self.logger.debug(f"Tool {tool.name} has schema: {tool_info['inputSchema']}")

            tools_list.append(tool_info)

        result = {"tools": tools_list}
        self.logger.info(f"Returning {len(tools_list)} tools to client")
        return result
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        self.logger.info(f"Tool call requested: {name} with args: {arguments}")

        if name not in self.tools:
            self.logger.error(f"Tool '{name}' not found. Available tools: {list(self.tools.keys())}")
            raise ValueError(f"Tool '{name}' not found")
        
        tool = self.tools[name]
        self.logger.debug(f"Retrieved tool: {tool.name}")

        try:
            # Call the tool with the provided arguments
            if hasattr(tool, 'args_schema') and tool.args_schema:
                self.logger.debug(f"Validating arguments against schema for tool: {name}")
                # Validate arguments against schema
                validated_args = tool.args_schema(**arguments)
                self.logger.debug(f"Validated args: {validated_args.model_dump()}")
                # Convert to dict and call tool async
                result = await tool._arun(**validated_args.model_dump())
            else:
                self.logger.debug(f"Calling tool {name} without schema validation")
                # Call tool directly with arguments async
                result = await tool._arun(**arguments)

            self.logger.info(f"Tool {name} executed successfully, result length: {len(str(result))}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
        except Exception as e:
            self.logger.error(f"Tool {name} execution failed: {str(e)}", exc_info=True)
            raise ValueError(f"Tool execution failed: {str(e)}")
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request."""
        self.logger.info(f"Handling MCP request: method={request.method}, id={request.id}")

        try:
            if request.method == "initialize":
                self.logger.info("Processing initialize request")
                # Handle MCP initialization
                tools_list = []
                for tool in self.tools.values():
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description,
                    }

                    # Add schema if available
                    if hasattr(tool, 'args_schema') and tool.args_schema:
                        tool_info["inputSchema"] = tool.args_schema.model_json_schema()

                    tools_list.append(tool_info)

                result = {
                    "protocolVersion": "2024-11-05",  # Use widely compatible MCP version
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "Yes Human MCP Server",
                        "version": "1.0.0"
                    }
                }
                self.logger.info(f"Initialize response: {result}")
            elif request.method == "tools/list":
                self.logger.info("Processing tools/list request")
                result = self.list_tools()
            elif request.method == "tools/call":
                name = request.params.get("name")
                arguments = request.params.get("arguments", {})
                self.logger.info(f"Processing tools/call for tool: {name}")
                result = await self.call_tool(name, arguments)
            elif request.method == "notifications/initialized":
                self.logger.info("Received notifications/initialized")
                # Handle initialization complete notification
                result = {}  # Empty response for notification
            else:
                self.logger.warning(f"Unknown method: {request.method}")
                return MCPResponse(
                    jsonrpc="2.0",
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    },
                    id=request.id
                )

            self.logger.info(f"Request {request.method} (id={request.id}) completed successfully")
            return MCPResponse(jsonrpc="2.0", result=result, id=request.id)

        except Exception as e:
            self.logger.error(f"Request {request.method} (id={request.id}) failed: {str(e)}", exc_info=True)
            return MCPResponse(
                jsonrpc="2.0",
                error={
                    "code": -32603,
                    "message": str(e)
                },
                id=request.id
            )


# Global MCP server instance
import logging
import sys
logger = logging.getLogger(__name__)

try:
    print("🔧 Initializing MCP server...", file=sys.stderr)
    logger.info("Creating global MCP server instance with tools:")
    for tool in MCP_TOOLS:
        logger.info(f"  - {tool.name}: {tool.description}")
        print(f"📋 Tool loaded: {tool.name}", file=sys.stderr)

    mcp_server = MCPServer(MCP_TOOLS)
    logger.info("✅ MCP server instance created successfully")
    print("✅ MCP server instance created successfully", file=sys.stderr)

except Exception as e:
    logger.error(f"❌ Failed to create MCP server: {str(e)}", exc_info=True)
    print(f"❌ Failed to create MCP server: {str(e)}", file=sys.stderr)
    # Create with empty tools as fallback
    logger.warning("Creating MCP server with empty tools as fallback")
    mcp_server = MCPServer([])
    logger.info("⚠️ MCP server created with empty tools (fallback mode)")
    print("⚠️ MCP server created with empty tools (fallback mode)", file=sys.stderr)
