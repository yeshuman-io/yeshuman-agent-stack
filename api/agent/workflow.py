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

    # Simple tools node that executes tools manually
    async def tools_node_with_logging(state: Any):
        """Tools node that executes tools manually instead of using ToolNode."""
        from .services import tools
        import logging
        logger = logging.getLogger('agent')

        logger.info("🛠️ Tools node called")

        # Extract user and focus from state (same as agent node)
        user = state.get("user")
        focus = None  # Will be determined from user context
        protocol = "graph"

        # Load tools dynamically
        tools_list = await tools.get_tools_for_request(user, focus, protocol)
        logger.info(f"🔧 Loaded {len(tools_list)} tools: {[t.name for t in tools_list]}")

        # Create a tool map for execution
        tool_map = {tool.name: tool for tool in tools_list}

        writer = state.get("writer")

        # Process tool calls from the last message
        tool_responses = []
        if state.get('messages'):
            last_message = state['messages'][-1]
            tool_calls = getattr(last_message, 'tool_calls', None) or []

            if tool_calls:
                logger.info(f"📋 Processing {len(tool_calls)} tool calls")

                # Voice status for tools phase
                tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                sig = f"tools:{','.join(sorted(tool_names))}"
                if writer and state.get("last_voice_sig") != sig:
                    writer({"type": "voice", "content": f"Calling {', '.join(tool_names)}..."})
                    state["last_voice_sig"] = sig

                # Execute each tool call
                for i, tc in enumerate(tool_calls):
                    tool_name = tc.get("name", "unknown")
                    tool_id = tc.get("id", "no_id")
                    tool_args = tc.get("args", tc.get("arguments", {}))

                    logger.info(f"🔧 Tool call {i+1}: {tool_name} (id: {tool_id})")
                    logger.info(f"🔧 Tool args: {tool_args}")

                    try:
                        if tool_name in tool_map:
                            tool = tool_map[tool_name]

                            # Inject user_id if needed
                            if tool_name in ["update_user_profile", "manage_user_profile"]:
                                if user and not tool_args.get("user_id"):
                                    tool_args["user_id"] = user.id
                                    logger.info(f"👤 Injected user_id {user.id} into {tool_name} call")

                            # Execute the tool
                            result = await tool.ainvoke(tool_args)
                            logger.info(f"✅ Tool {tool_name} executed successfully")

                            # Create tool response message
                            from langchain_core.messages import ToolMessage
                            tool_response = ToolMessage(
                                content=str(result),
                                tool_call_id=tool_id,
                                name=tool_name
                            )
                            tool_responses.append(tool_response)
                        else:
                            logger.error(f"❌ Tool {tool_name} not found in available tools")
                            from langchain_core.messages import ToolMessage
                            tool_response = ToolMessage(
                                content=f"Error: Tool {tool_name} not available",
                                tool_call_id=tool_id,
                                name=tool_name
                            )
                            tool_responses.append(tool_response)

                    except Exception as e:
                        logger.error(f"❌ Tool {tool_name} execution failed: {str(e)}")
                        from langchain_core.messages import ToolMessage
                        tool_response = ToolMessage(
                            content=f"Error: {str(e)}",
                            tool_call_id=tool_id,
                            name=tool_name
                        )
                        tool_responses.append(tool_response)

                # Send completion status
                if writer:
                    completed_tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                    writer({"type": "tool_complete", "content": f"✅ Completed tools: {', '.join(completed_tool_names)}"})

            else:
                logger.warning("⚠️ Tools node called but no tool calls found in last message")
        else:
            logger.warning("⚠️ Tools node called but no messages in state")

        # Return updated state with tool responses
        result = {
            "messages": state["messages"] + tool_responses,
            "writer": writer,
            "tools_done": False,  # Allow iterative tool usage
            "tool_call_count": state.get("tool_call_count", 0) + 1
        }

        # Carry forward voice state
        if state.get("last_voice_sig"):
            result["last_voice_sig"] = state.get("last_voice_sig")
        if state.get("voice_messages"):
            result["voice_messages"] = state.get("voice_messages")

        logger.info(f"🎯 Tools node completed with {len(tool_responses)} responses")
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
