"""
Agent interaction tools for the YesHuman agent.
These tools are separate to avoid circular imports.
"""
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional


class AgentInteractionInput(BaseModel):
    """Input for agent interaction tool."""
    message: str = Field(description="Message to send to the YesHuman agent")


class AgentInteractionTool(BaseTool):
    """Tool for direct interaction with the YesHuman agent."""
    
    name: str = "agent_chat"
    description: str = "Chat directly with the YesHuman agent. Ask questions, request demonstrations of capabilities, or have a conversation."
    args_schema: type[BaseModel] = AgentInteractionInput
    
    def _run(self, message: str, run_manager: Optional = None) -> str:
        """Execute the agent interaction tool synchronously (wrapper for async version)."""
        import asyncio
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't be called
            return "Error: Synchronous tool execution not supported in async context"
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._arun(message, run_manager))
    
    async def _arun(self, message: str, run_manager: Optional = None) -> str:
        """Execute the agent interaction tool asynchronously."""
        try:
            # Import here to avoid circular imports
            from agent.graph import ainvoke_agent
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Now we can properly call the async function
            result = await ainvoke_agent(message)
            if result["success"]:
                return result["response"]
            else:
                return f"Agent Error: {result['error']}"
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AgentInteractionTool execution error: {str(e)}")
            return "AgentChat temporarily unavailable"


class AgentCapabilitiesInput(BaseModel):
    """Input for agent capabilities tool."""
    detail_level: str = Field(
        default="summary", 
        description="Level of detail: 'summary' for overview, 'detailed' for full capabilities"
    )


class AgentCapabilitiesTool(BaseTool):
    """Tool for discovering agent capabilities."""
    
    name: str = "agent_capabilities"
    description: str = "Get information about the YesHuman agent's capabilities and available tools."
    args_schema: type[BaseModel] = AgentCapabilitiesInput
    
    def _run(self, detail_level: str = "summary", run_manager: Optional = None) -> str:
        """Execute the agent capabilities tool synchronously (wrapper for async version)."""
        import asyncio
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't be called
            return "Error: Synchronous tool execution not supported in async context"
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._arun(detail_level, run_manager))
    
    async def _arun(self, detail_level: str = "summary", run_manager: Optional = None) -> str:
        """Execute the agent capabilities tool."""
        try:
            import asyncio
            await asyncio.sleep(0)  # Yield control
            # Get basic tools to avoid circular import
            from tools.utilities import CalculatorTool, EchoTool
            basic_tools = [CalculatorTool(), EchoTool()]
            
            if detail_level == "detailed":
                capabilities = {
                    "agent_info": {
                        "name": "YesHuman Agent",
                        "type": "LangGraph ReAct Agent",
                        "model": "gpt-4o-mini",
                        "capabilities": [
                            "Natural language conversation",
                            "Tool usage and coordination", 
                            "Mathematical calculations",
                            "Problem solving",
                            "Information processing",
                            "Agent-to-agent communication",
                            "Cross-platform deployment"
                        ]
                    },
                    "available_tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "schema": tool.args_schema.model_json_schema() if tool.args_schema else None
                        }
                        for tool in basic_tools
                    ] + [
                        {
                            "name": "agent_chat",
                            "description": "Direct interaction with the YesHuman agent",
                            "schema": AgentInteractionInput.model_json_schema()
                        },
                        {
                            "name": "agent_capabilities", 
                            "description": "Get agent capabilities information",
                            "schema": AgentCapabilitiesInput.model_json_schema()
                        }
                    ],
                    "access_methods": [
                        "MCP Protocol (Model Context Protocol)",
                        "A2A Protocol (Agent-to-Agent)",
                        "REST API",
                        "Direct Python integration"
                    ],
                    "deployment_targets": [
                        "Cursor IDE",
                        "Claude Desktop",
                        "Other AI platforms via A2A",
                        "Web applications",
                        "Mobile applications"
                    ]
                }
                return f"YesHuman Agent Detailed Capabilities:\n{capabilities}"
            else:
                tool_names = [tool.name for tool in basic_tools] + ["agent_chat", "agent_capabilities"]
                return f"""YesHuman Agent - Capabilities Summary:
                
🤖 **Agent Type**: LangGraph ReAct Agent with GPT-4o-mini
🛠️ **Available Tools**: {', '.join(tool_names)}
🔗 **Access Methods**: MCP, A2A, REST API
💬 **Core Features**: Natural conversation, tool coordination, problem solving
🌐 **Deployment**: Multi-platform agent stack (Cursor, Claude Desktop, A2A platforms)

For detailed capabilities, use detail_level='detailed'
To chat directly with the agent, use the 'agent_chat' tool."""
                
        except Exception as e:
            return f"Error retrieving capabilities: {str(e)}"


# Export agent-specific tools
AGENT_TOOLS = [
    AgentInteractionTool(),
    AgentCapabilitiesTool(),
]
