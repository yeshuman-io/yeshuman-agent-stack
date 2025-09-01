"""
Yes Human Agent - Simple ReAct Implementation with LangGraph.

Clean design following LangGraph patterns:
- Standard AgentState with messages + add_messages reducer
- Simple nodes: context preparation, agent, tools
- Built-in ToolNode for tool execution
- Proper streaming integration
"""
import os
import logging
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode

from tools.utilities import AVAILABLE_TOOLS

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger('agent')
# Module-local, async-safe-ish voice state store keyed by user_id
# Keeps minimal state across graph turns without coupling to graph state
VOICE_STATE: Dict[str, Dict[str, Any]] = {}

def _get_voice_state(user_id: str) -> Dict[str, Any]:
    if user_id not in VOICE_STATE:
        VOICE_STATE[user_id] = {
            "voice_messages": [],
            "last_voice_sig": None,
        }
    return VOICE_STATE[user_id]


# Dynamic system prompt based on client configuration
def get_system_prompt():
    """Get the system prompt for the current client configuration."""
    try:
        from django.conf import settings
        # Check if settings are configured
        if hasattr(settings, 'CURRENT_CLIENT'):
            return settings.CURRENT_CLIENT['system_prompt']
        else:
            # Django settings not fully loaded yet
            return get_fallback_prompt()
    except (ImportError, AttributeError):
        # Django not available or not configured
        return get_fallback_prompt()

def get_fallback_prompt():
    """Fallback system prompt when Django settings unavailable."""
    return """You are an AI assistant without a name.

Address the user as "Human" or "human".
Don't use synonyms "human".
Use different punctuations for "yes" and "human" such as ' ! , . ; ?.
Subtly borrow terminology and language patterns from Blade Runner and Dune without directly referencing these works by name.
Be subtle, don't over do it.  Be minimal and slightly robotic.  Be dead pan without exclamations."""

# Initialize with fallback, will be updated when Django is ready
SYSTEM_PROMPT = get_fallback_prompt()


class AgentState(TypedDict):
    """Simple state following LangGraph patterns."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]
    tools_done: Optional[bool]
    voice_messages: Optional[List[str]]
    last_voice_sig: Optional[str]


async def context_preparation_node(state: AgentState) -> AgentState:
    """Add system prompt to start conversation."""
    global SYSTEM_PROMPT

    # Try to refresh system prompt from Django settings if available
    try:
        current_prompt = get_system_prompt()
        if current_prompt != SYSTEM_PROMPT:
            SYSTEM_PROMPT = current_prompt
            print(f"✅ Updated system prompt for client configuration")
    except Exception:
        # Keep existing prompt if update fails
        pass

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
        # Voice generation (enabled): brief background status line per agent_node
        voice_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=api_key,
            streaming=True,
        )
        # Rate-limit by phase signature using process-local VOICE_STATE
        user_id = state.get("user_id") or "default"
        vs = _get_voice_state(user_id)
        phase_sig = "agent:final" if state.get("tools_done") else "agent:start"
        if vs.get("last_voice_sig") != phase_sig:
            import asyncio as _asyncio
            async def _voice_task():
                try:
                    logger.info(f"Voice task started for phase: {phase_sig}")
                    # Context for a brief progress prompt
                    user_msg = ""
                    for _m in reversed(state.get("messages", [])):
                        if isinstance(_m, HumanMessage):
                            user_msg = _m.content
                            break
                    prior_voice = "\n".join(vs.get("voice_messages", []) or [])
                    prompt = (
                        "You are generating a single brief status line (2-10 words) that updates the user "
                        "on agent progress. Consider previous voice lines and avoid repeating similar lines.\n\n"
                        f"Previous lines (most recent last):\n{prior_voice if prior_voice else '(none)'}\n\n"
                        f"Current user request: {user_msg}\n"
                        "Return ONLY the status line, no quotes."
                    )
                    new_line = ""
                    # Signal start of a new voice segment
                    if writer:
                        logger.info("Sending voice_start signal")
                        writer({"type": "voice_start"})
                    async for _chunk in voice_llm.astream([HumanMessage(content=prompt)]):
                        if _chunk.content:
                            new_line += _chunk.content
                            if writer:
                                logger.info(f"Sending voice chunk: {_chunk.content}")
                                writer({"type": "voice", "content": _chunk.content})
                    # Persist
                    new_line_clean = (new_line or "").strip()
                    last_line = (vs.get("voice_messages", []) or [])[-1] if vs.get("voice_messages") else ""
                    if new_line_clean and new_line_clean.lower() != (last_line or "").strip().lower():
                        vs.setdefault("voice_messages", []).append(new_line_clean)
                    vs["last_voice_sig"] = phase_sig
                    # Signal voice segment completion
                    if writer:
                        logger.info("Sending voice_stop signal")
                        writer({"type": "voice_stop"})
                    logger.info(f"Voice task completed: {new_line_clean}")
                except Exception as _e:
                    logger.error(f"Voice generation error: {_e}")
            _asyncio.create_task(_voice_task())
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
            temperature=1,
            api_key=api_key,
            streaming=True,
        )

        final_response = None
        async for chunk in final_llm.astream(state["messages"]):
            if chunk.content and writer:
                writer({"type": "message", "content": chunk.content})
            final_response = chunk

        logger.info("Agent response completed")
        return {
            "messages": [final_response],
            "writer": writer,
            "voice_messages": state.get("voice_messages", []),
            "last_voice_sig": state.get("last_voice_sig"),
        }
        
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
                # Voice status for tools phase (single line, rate-limited by phase signature)
                tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                sig = f"tools:{','.join(sorted(tool_names))}"
                if writer and state.get("last_voice_sig") != sig:
                    writer({"type": "voice", "content": f"Calling {', '.join(tool_names)}..."})
                    state["last_voice_sig"] = sig
        
        result = base_tool_node.invoke(state)

        # Mark tools as executed to bound the loop and carry voice state forward
        result["tools_done"] = True
        if state.get("last_voice_sig"):
            result["last_voice_sig"] = state.get("last_voice_sig")
        if state.get("voice_messages"):
            result["voice_messages"] = state.get("voice_messages")

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
async def ainvoke_agent(message: str, messages: Optional[List[BaseMessage]] = None, agent=None):
    """Async invoke the agent with a message."""
    if agent is None:
        agent = create_agent()

    # Use provided messages or create new message list
    if messages:
        state_messages = messages + [HumanMessage(content=message)]
    else:
        state_messages = [HumanMessage(content=message)]

    state = {
        "messages": state_messages,
        "user_id": None
    }

    result = await agent.ainvoke(state)
    return result


async def ainvoke_agent_sync(message: str, messages: Optional[List[BaseMessage]] = None):
    """Synchronous version of agent for thread API - returns complete response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not configured")

    # Use provided messages or create new message list
    if messages:
        state_messages = messages + [HumanMessage(content=message)]
    else:
        state_messages = [HumanMessage(content=message)]

    # Add system message if not present
    if not state_messages or not isinstance(state_messages[0], SystemMessage):
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        state_messages = [system_message] + state_messages

    # Create a synchronous LLM for complete responses
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=1,
        api_key=api_key,
        streaming=False,  # No streaming for complete responses
    )

    # Get the complete response
    response = await llm.ainvoke(state_messages)

    # Return in the same format as the graph agent
    return {
        "messages": [response],
        "user_id": None,
        "tools_done": True,
        "voice_messages": [],
        "last_voice_sig": None
    }


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


async def astream_agent_tokens(message: str, messages: Optional[List[BaseMessage]] = None, agent=None):
    """Stream agent tokens - unified writer() approach."""
    if agent is None:
        agent = create_agent()

    # Use provided messages or create new message list
    if messages:
        state_messages = messages + [HumanMessage(content=message)]
    else:
        state_messages = [HumanMessage(content=message)]

    state = {
        "messages": state_messages,
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