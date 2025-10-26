"""
Workflow composition for the agent.

Builds and compiles the LangGraph workflow from individual nodes.
"""

import logging
from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .graph import AgentState, context_preparation_node, agent_node, should_continue
from .checkpointer import DjangoCheckpointSaver

logger = logging.getLogger('agent')


def build_workflow() -> StateGraph:
    """
    Build the LangGraph workflow with all nodes and edges.

    Returns:
        Configured StateGraph ready for compilation
    """
    logger.info("🏗️ Building agent workflow...")

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("context_preparation", context_preparation_node)
    workflow.add_node("agent", agent_node)

    # Create tools node dynamically (will be created in the tools node function)
    async def tools_node_with_logging(state: Any, config: Any):
        """Tools node that loads tools dynamically based on context."""
        from .services import tools
        from .mapper import get_tool_event_config
        import logging
        logger = logging.getLogger('agent')

        logger.info("🛠️ Tools node called")

        # Extract user and focus from config for dynamic tool loading
        configurable = config.get("configurable", {})
        user = configurable.get("user")
        focus = configurable.get("focus")
        protocol = configurable.get("protocol", "graph")

        # Load tools dynamically (same logic as agent node)
        tools_list = await tools.get_tools_for_request(user, focus, protocol)

        # Create ToolNode with the dynamically loaded tools
        base_tool_node = ToolNode(tools_list)

        writer = state.get("writer")

        if state.get('messages'):
            last_message = state['messages'][-1]
            tool_calls = getattr(last_message, 'tool_calls', None) or []
            if tool_calls:
                logger.info(f"📋 Processing {len(tool_calls)} tool calls")
                for i, tc in enumerate(tool_calls):
                    tool_name = tc.get("name", "unknown")
                    tool_id = tc.get("id", "no_id")
                    tool_args = tc.get("args", tc.get("arguments", {}))
                    logger.info(f"🔧 Tool call {i+1}: {tool_name} (id: {tool_id})")
                    if tool_args == {} or not tool_args:
                        logger.warning(f"⚠️ Tool call {i+1} has empty arguments: {tool_args} (type: {type(tool_args)})")
                    else:
                        logger.info(f"🔧 Tool args for {tool_name}: {tool_args} (type: {type(tool_args)})")
                    if isinstance(tool_args, str) and tool_args:
                        import json
                        try:
                            parsed_args = json.loads(tool_args)
                            logger.info(f"🔧 Parsed JSON args for {tool_name}: {parsed_args}")
                        except json.JSONDecodeError as e:
                            logger.error(f"🔧 Failed to parse tool args JSON for {tool_name}: {e}")

                # Voice status for tools phase (single line, rate-limited by phase signature)
                tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                sig = f"tools:{','.join(sorted(tool_names))}"
                if writer and state.get("last_voice_sig") != sig:
                    writer({"type": "voice", "content": f"Calling {', '.join(tool_names)}..."})
                    state["last_voice_sig"] = sig
            else:
                logger.warning("⚠️ Tools node called but no tool calls found in last message")
        else:
            logger.warning("⚠️ Tools node called but no messages in state")

        logger.info("⚙️ Invoking ToolNode...")
        try:
            result = await base_tool_node.ainvoke(state)
            logger.info("✅ ToolNode invocation completed")

            # Check the result messages for tool responses
            if result.get('messages'):
                tool_responses = [msg for msg in result['messages'] if hasattr(msg, 'tool_call_id')]
                logger.info(f"📨 Received {len(tool_responses)} tool response messages")
                for i, response in enumerate(tool_responses):
                    tool_call_id = getattr(response, 'tool_call_id', 'no_id')
                    content_preview = str(response.content)[:100] if response.content else "No content"
                    # Check if this is an error response
                    if str(response.content).startswith("Error:"):
                        logger.error(f"❌ Tool response {i+1}: id={tool_call_id}, content_preview='{content_preview}...'")
                    else:
                        logger.info(f"📨 Tool response {i+1}: id={tool_call_id}, content_preview='{content_preview}...'")
            else:
                logger.warning("⚠️ ToolNode returned no messages")

        except Exception as e:
            logger.error(f"❌ ToolNode invocation failed: {str(e)}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            raise

        # UI events are now emitted in the agent node after tools complete

        # Emit tool completion event
        if writer and state.get('messages'):
            last_message = state['messages'][-1]
            tool_calls = getattr(last_message, 'tool_calls', None) or []
            if tool_calls:
                completed_tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                writer({"type": "tool_complete", "content": f"✅ Completed tools: {', '.join(completed_tool_names)}"})

        # Allow iterative tool usage - don't set tools_done
        # Carry voice state forward
        if state.get("last_voice_sig"):
            result["last_voice_sig"] = state.get("last_voice_sig")
        if state.get("voice_messages"):
            result["voice_messages"] = state.get("voice_messages")

        # Check if any tool responses were errors
        has_errors = False
        if result.get('messages'):
            for msg in result['messages']:
                if hasattr(msg, 'content') and str(msg.content).startswith("Error:"):
                    has_errors = True
                    break

        if has_errors:
            logger.warning("⚠️ Tools node completed with errors - some tools failed")
        else:
            logger.info("🎯 Tools node completed successfully")
        return result

    workflow.add_node("tools", tools_node_with_logging)

    # Define flow
    workflow.set_entry_point("context_preparation")
    workflow.add_edge("context_preparation", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "agent")  # After tools, back to agent

    logger.info("✅ Workflow built successfully")
    return workflow


async def create_agent(*args, **kwargs):
    """
    Create and return the compiled agent with Django checkpointer.

    This is a convenience wrapper around build_workflow().compile().
    """
    logger.info("🎯 Creating compiled agent...")

    workflow = build_workflow()

    # Create Django-based checkpointer for persistence (singleton)
    checkpointer = DjangoCheckpointSaver.get_instance()

    agent = workflow.compile(checkpointer=checkpointer)
    logger.info("🎉 Agent created and compiled successfully")
    return agent
