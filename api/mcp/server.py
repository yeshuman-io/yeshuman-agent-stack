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
        self.tools = {tool.name: tool for tool in tools}
    
    def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
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
        
        return {
            "tools": tools_list
        }
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        
        tool = self.tools[name]
        
        try:
            # Call the tool with the provided arguments
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # Validate arguments against schema
                validated_args = tool.args_schema(**arguments)
                # Convert to dict and call tool async
                result = await tool._arun(**validated_args.model_dump())
            else:
                # Call tool directly with arguments async
                result = await tool._arun(**arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
        except Exception as e:
            raise ValueError(f"Tool execution failed: {str(e)}")
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request."""
        try:
            if request.method == "initialize":
                # Handle MCP initialization
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "Yes Human",
                        "version": "1.0.0"
                    }
                }
            elif request.method == "tools/list":
                result = self.list_tools()
            elif request.method == "tools/call":
                name = request.params.get("name")
                arguments = request.params.get("arguments", {})
                result = await self.call_tool(name, arguments)
            elif request.method == "notifications/initialized":
                # Handle initialization complete notification
                result = {}  # Empty response for notification
            else:
                return MCPResponse(
                    jsonrpc="2.0",
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    },
                    id=request.id
                )
            
            return MCPResponse(jsonrpc="2.0", result=result, id=request.id)
        
        except Exception as e:
            return MCPResponse(
                jsonrpc="2.0",
                error={
                    "code": -32603,
                    "message": str(e)
                },
                id=request.id
            )


# Global MCP server instance
mcp_server = MCPServer(MCP_TOOLS)
