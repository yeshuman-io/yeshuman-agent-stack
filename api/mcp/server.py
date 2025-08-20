"""
MCP Server implementation using Django Ninja and BaseTool tools.
"""
from ninja import NinjaAPI, Schema
from typing import Dict, Any, List, Optional
from tools.utilities import AVAILABLE_TOOLS
from langchain_core.tools import BaseTool
import json


class MCPRequest(Schema):
    """Base MCP request schema."""
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[str] = None


class MCPResponse(Schema):
    """Base MCP response schema."""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


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
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        
        tool = self.tools[name]
        
        try:
            # Call the tool with the provided arguments
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # Validate arguments against schema
                validated_args = tool.args_schema(**arguments)
                # Convert to dict and call tool
                result = tool._run(**validated_args.model_dump())
            else:
                # Call tool directly with arguments
                result = tool._run(**arguments)
            
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
    
    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request."""
        try:
            if request.method == "tools/list":
                result = self.list_tools()
            elif request.method == "tools/call":
                name = request.params.get("name")
                arguments = request.params.get("arguments", {})
                result = self.call_tool(name, arguments)
            else:
                return MCPResponse(
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    },
                    id=request.id
                )
            
            return MCPResponse(result=result, id=request.id)
        
        except Exception as e:
            return MCPResponse(
                error={
                    "code": -32603,
                    "message": str(e)
                },
                id=request.id
            )


# Global MCP server instance
mcp_server = MCPServer(AVAILABLE_TOOLS)
