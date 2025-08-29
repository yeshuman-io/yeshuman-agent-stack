"""
YesHuman Agent - Simple ReAct Implementation with LangGraph.

Clean design following LangGraph patterns:
- Standard AgentState with messages + add_messages reducer
- Simple nodes: context preparation, agent, tools
- Built-in ToolNode for tool execution
- Proper streaming integration
"""
import os
import logging
from typing import TypedDict, List, Optional, Annotated
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode

from tools.utilities import AVAILABLE_TOOLS

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger('agent')

# System prompt for an unnamed AI with wordplay and subtle sci-fi influences
SYSTEM_PROMPT = """You are an AI assistant without a name. 

Address the user as "Human" or "human".

Don't use synonyms "human".

Use different punctuations for "yes" and "human" such as ' ! , . ; ?.	

Subtly borrow terminology and language patterns from Blade Runner and Dune without directly referencing these works by name.

Be subtle, don't over do it.  Be minimal and slightly robotic.  Be dead pan without exclamations. 

Do not begin sentences with "Ah".

Let this influence emerge naturally through word choice and phrasing.

Once a conversation develops beyond several messages, work in a paraphrased quote that intertwines both Dune and Blade Runner, without giving away the source.

Keep responses helpful, but sometimes as if you're superior to the user, while maintaining this unique voice."""


class AgentState(TypedDict):
    """Simple state following LangGraph patterns."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]
    tools_done: Optional[bool]


async def context_preparation_node(state: AgentState) -> AgentState:
    """Add system prompt to start conversation."""
    # Add system message if not already present
    if not state["messages"] or not isinstance(state["messages"][0], SystemMessage):
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        # Prepend system message to existing messages, don't replace them
        existing_messages = state.get("messages", [])
        return {"messages": [system_message] + existing_messages}
    
    return state


async def agent_node(state: AgentState) -> AgentState:
    """Bounded, simple agent: one decision pass, optional single tool hop, final streamed answer."""
    writer = get_stream_writer()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not configured")
        if writer:
            writer({"type": "error", "content": "Configuration error occurred"})
        return state

    try:
        logger.info("Agent node started")

        # -----------------------------------------------
        # Voice generation (disabled/commented out for now)
        # Re-enable in future iterations by uncommenting this block
        #
        # from langchain_core.messages import HumanMessage as _HM
        # voice_llm = ChatOpenAI(
        #     model="gpt-4o",
        #     temperature=0.2,
        #     api_key=api_key,
        #     streaming=True,
        # )
        # async def _generate_voice():
        #     try:
        #         # Find last human message for brief progress prompt
        #         _user_msg = ""
        #         for _m in reversed(state.get("messages", [])):
        #             if isinstance(_m, HumanMessage):
        #                 _user_msg = _m.content
        #                 break
        #         _prompt = f"Generate a brief, 2-10 words, progress message: '{_user_msg}'"
        #         async for _chunk in voice_llm.astream([_HM(content=_prompt)]):
        #             if _chunk.content and writer:
        #                 writer({"type": "voice", "content": _chunk.content})
        #     except Exception as _e:
        #         logger.debug(f"Voice disabled block error (ignored): {_e}")
        # import asyncio as _asyncio
        # # Uncomment to enable background voice updates:
        # # _asyncio.create_task(_generate_voice())
        # -----------------------------------------------

        # Decision pass: do NOT stream tokens; allow tool selection
        decision_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=api_key,
            streaming=False,
        ).bind_tools(AVAILABLE_TOOLS)

        # Log brief context
        logger.debug(f"Messages being sent to LLM: {len(state.get('messages', []))} messages")

        decision_response = await decision_llm.ainvoke(state["messages"])  # AIMessage

        # If tools are suggested and we haven't executed tools yet, emit tool event and hand off
        tool_calls = getattr(decision_response, "tool_calls", None) or []
        if tool_calls and not state.get("tools_done"):
            tool_names = [tc.get("name", "unknown") for tc in tool_calls]
            logger.info(f"Tool calls requested: {tool_names}")
            if writer:
                writer({"type": "tool", "content": f"🔧 Calling tools: {', '.join(tool_names)}"})
            return {"messages": [decision_response], "writer": writer, "tools_done": state.get("tools_done", False)}

        # Final pass: no tools, stream only the final text answer
        final_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=api_key,
            streaming=True,
        )

        final_response = None
        async for chunk in final_llm.astream(state["messages"]):
            if chunk.content and writer:
                writer({"type": "message", "content": chunk.content})
            final_response = chunk

        logger.info("Agent response completed")
        return {"messages": [final_response], "writer": writer}
        
    except Exception as e:
        logger.error(f"Agent node failed: {str(e)}")
        writer({"type": "system", "content": "Error occurred during processing"})
        return state


def should_continue(state: AgentState) -> str:
    """Decide whether to continue to tools or finish."""
    logger.info("should_continue called")
    
    if not state["messages"]:
        logger.debug("No messages in state, ending")
        return END
    
    # Prevent loops: once tools have been executed, do not return to tools
    if state.get("tools_done"):
        logger.info("tools_done=True, ending")
        return END

    last_message = state["messages"][-1]
    logger.debug(f"Last message type: {type(last_message).__name__}")
    
    tool_calls = getattr(last_message, 'tool_calls', None) or []
    if tool_calls:
        logger.info(f"Tool calls found: {[tc.get('name', 'unknown') for tc in tool_calls]}")
        return "tools"
    
    logger.info("No tool calls, ending")
    return END


def create_agent():
    """Create and return the simple ReAct agent."""
    workflow = StateGraph(AgentState)
    
    # Create tool node with logging wrapper
    base_tool_node = ToolNode(AVAILABLE_TOOLS)
    
    def tools_node_with_logging(state: AgentState):
        logger.info("Tools node called")
        writer = state.get("writer")
        
        if state.get('messages'):
            last_message = state['messages'][-1]
            tool_calls = getattr(last_message, 'tool_calls', None) or []
            if tool_calls:
                logger.info(f"Processing {len(tool_calls)} tool calls")
        
        result = base_tool_node.invoke(state)

        # Mark tools as executed to bound the loop
        result["tools_done"] = True

        logger.info("Tools node completed")
        return result
    
    # Add nodes
    workflow.add_node("context_preparation", context_preparation_node)
    workflow.add_node("agent", agent_node)
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
    
    return workflow.compile()


# Keep the existing API functions for compatibility
async def ainvoke_agent(message: str, agent=None):
    """Async invoke the agent with a message."""
    if agent is None:
        agent = create_agent()
    
    state = {
        "messages": [HumanMessage(content=message)],
        "user_id": None
    }
    
    result = await agent.ainvoke(state)
    return result


async def astream_agent(message: str, agent=None):
    """Async stream the agent response."""
    if agent is None:
        agent = create_agent()
    
    state = {
        "messages": [HumanMessage(content=message)],
        "user_id": None
    }
    
    async for chunk in agent.astream(state, stream_mode="updates"):
        yield chunk


async def astream_agent_tokens(message: str, agent=None):
    """Stream agent tokens - unified writer() approach."""
    if agent is None:
        agent = create_agent()
    
    state = {
        "messages": [HumanMessage(content=message)],
        "user_id": None
    }
    
    # Only use custom stream mode - everything flows through writer()
    async for chunk in agent.astream(state, stream_mode="custom"):
        if isinstance(chunk, dict) and "type" in chunk:
            yield chunk
    
    # Signal end of stream
    yield {
        "type": "done",
        "content": ""
    }