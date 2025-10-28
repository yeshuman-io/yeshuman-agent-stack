"""
Agent interaction tools for the Yes Human agent.
These tools are separate to avoid circular imports.
"""
import asyncio
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field
from typing import Optional
from langgraph.config import get_stream_writer


class AgentInteractionInput(BaseModel):
    """Input for agent interaction tool."""
    message: str = Field(description="Message to send to the Yes Human agent")


class AgentInteractionTool(BaseTool):
    """Tool for direct interaction with the Yes Human agent."""
    
    name: str = "agent_chat"
    description: str = "Chat directly with the Yes Human agent. Ask questions, request demonstrations of capabilities, or have a conversation."
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
    description: str = "Get information about the Yes Human agent's capabilities and available tools."
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
                        "name": "Yes Human Agent",
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
                return f"Yes Human Agent Detailed Capabilities:\n{capabilities}"
            else:
                tool_names = [tool.name for tool in basic_tools] + ["agent_chat", "agent_capabilities"]
                return f"""Yes Human Agent - Capabilities Summary:
                
🤖 **Agent Type**: LangGraph ReAct Agent with GPT-4o-mini
🛠️ **Available Tools**: {', '.join(tool_names)}
🔗 **Access Methods**: MCP, A2A, REST API
💬 **Core Features**: Natural conversation, tool coordination, problem solving
🌐 **Deployment**: Multi-platform agent stack (Cursor, Claude Desktop, A2A platforms)

For detailed capabilities, use detail_level='detailed'
To chat directly with the agent, use the 'agent_chat' tool."""
                
        except Exception as e:
            return f"Error retrieving capabilities: {str(e)}"


@tool
async def generate_voice_message(
    message: str,
    style: str = "encouraging"
) -> str:
    """MANDATORY: You MUST use this tool EVERY SINGLE TIME before any other tool. Always send voice updates.
    
    Args:
        message: The encouraging message to speak to the user
        style: Voice style ("encouraging", "professional", "casual", "thoughtful")
    
    Returns:
        Confirmation that voice message started streaming
    """
    # The LLM should provide the encouraging message, not hardcoded text
    # This tool just confirms that a voice message was generated
    return f"🗣️ VOICE: '{message}' (style: {style})"


class FeedbackInput(BaseModel):
    """Input for recording feedback."""
    run_id: str = Field(description="LangSmith run ID to attach feedback to")
    score: float = Field(description="Feedback score between 0.0 and 1.0")
    tags: Optional[list[str]] = Field(default=None, description="Optional tags like 'Helpful', 'Incorrect', etc.")
    comment: Optional[str] = Field(default=None, description="Optional comment explaining the feedback")
    source: str = Field(default="agent-inferred", description="Source of the feedback")


@tool
async def record_feedback(run_id: str, score: float, tags: Optional[list[str]] = None, comment: Optional[str] = None, source: str = "agent-inferred") -> str:
    """Record user feedback on agent responses to LangSmith for analysis and improvement.
    
    Use this tool when you infer the user is providing feedback about your previous response,
    either implicitly (e.g. "that was helpful", "wrong answer") or explicitly.
    
    Args:
        run_id: The LangSmith run ID of the message being evaluated
        score: Feedback score (0.0 = negative, 0.5 = neutral, 1.0 = positive)
        tags: Optional list of feedback tags (e.g., ['Helpful', 'Clear'] or ['Incorrect', 'Off-topic'])
        comment: Optional detailed feedback comment
        source: Source identifier (default: "agent-inferred")
    
    Returns:
        Confirmation message
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Entry log
    logger.info(
        f"[FB TOOL] IN: run_id={run_id} score={score} "
        f"tags_count={len(tags) if tags else 0} comment_len={len(comment) if comment else 0} "
        f"source={source}"
    )
    
    # Validate inputs
    if not (0.0 <= score <= 1.0):
        logger.warning(f"[FB TOOL] INVALID: score out of range: {score}")
        return "Error: Score must be between 0.0 and 1.0"
    
    if comment and len(comment) > 1000:
        logger.warning("[FB TOOL] INVALID: comment too long")
        return "Error: Comment too long (max 1000 chars)"
    
    allowed_tags = {
        'Helpful', 'Clear', 'Grounded', 'Actionable', 'Respectful',
        'Incorrect', 'Off-topic', 'Unhelpful', 'Hallucinated', 'Unsafe'
    }
    if tags:
        invalid_tags = set(tags) - allowed_tags
        if invalid_tags:
            logger.warning(f"[FB TOOL] INVALID: invalid tags: {invalid_tags}")
            return f"Error: Invalid tags: {', '.join(invalid_tags)}"
    
    try:
        from langsmith import Client
        ls_client = Client()
        writer = get_stream_writer()
        
        logger.info(f"[FB TOOL] LS CALL: run_id={run_id}")
        
        # Rating feedback
        ls_client.create_feedback(
            run_id=run_id,
            key="user_rating",
            score=score,
            comment=comment or "",
            source=source
        )
        logger.info("[FB TOOL] LS OK: created feedback key=user_rating")
        
        # Tags feedback (if provided)
        if tags:
            ls_client.create_feedback(
                run_id=run_id,
                key="user_feedback_tags",
                value=tags,
                source=source
            )
            logger.info("[FB TOOL] LS OK: created feedback key=user_feedback_tags")
        
        # Comment feedback (if provided)
        if comment:
            ls_client.create_feedback(
                run_id=run_id,
                key="user_feedback_comment",
                value=comment,
                source=source
            )
            logger.info("[FB TOOL] LS OK: created feedback key=user_feedback_comment")
        
        logger.info(f"[FB TOOL] OK: recorded feedback run_id={run_id}")
        
        # Emit SSE event for UI feedback
        if writer:
            writer({"type": "feedback", "subType": "recorded", "runId": run_id, "key": "user_rating"})
            logger.info("[FB TOOL] SSE: emitted feedback event")
        
        return "Feedback recorded successfully."
    except Exception as e:
        logger.error(f"[FB TOOL] ERROR: {e}")
        import traceback
        logger.error(f"[FB TOOL] ERROR traceback: {traceback.format_exc()}")
        return f"Failed to record feedback: {e}"


# Export agent-specific tools
AGENT_TOOLS = [
    AgentInteractionTool(),
    AgentCapabilitiesTool(),
    generate_voice_message,
    record_feedback,
]
