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
import re
from typing import TypedDict, List, Optional, Annotated, Tuple
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
logger = logging.getLogger(__name__)

# Simple system prompt
SYSTEM_PROMPT = "You are Yes Human."


def parse_thinking_response(content: str) -> Tuple[str, str]:
    """
    Parse a response that may contain <thinking> tags.
    
    Returns:
        (thinking_content, message_content)
    """
    # Extract thinking content
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
    thinking_content = thinking_match.group(1).strip() if thinking_match else ""
    
    # Remove thinking tags from main content
    message_content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()
    
    return thinking_content, message_content





class AgentState(TypedDict):
    """Simple state following LangGraph patterns."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]


async def context_preparation_node(state: AgentState) -> AgentState:
    """Add system prompt to start conversation."""
    # Add system message if not already present
    if not state["messages"] or not isinstance(state["messages"][0], SystemMessage):
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        return {"messages": [system_message]}
    
    return state


async def agent_node(state: AgentState) -> AgentState:
    """LLM with tools - core ReAct logic."""
    writer = get_stream_writer()
    
    # Get LLM instance with tools bound
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not configured")
        writer({"type": "system", "content": "Configuration error occurred"})
        return state
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Back to working model for now
        temperature=0.1,
        api_key=api_key,
        streaming=True
    )
    
    # Bind tools to LLM - this is the proper ReAct pattern
    llm_with_tools = llm.bind_tools(AVAILABLE_TOOLS)
    
    try:
        # Just invoke - let LangGraph handle the streaming via stream_mode="messages"
        response = await llm_with_tools.ainvoke(state["messages"])
        
        # Use writer for system notifications
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_names = [tc["name"] for tc in response.tool_calls]
            writer({"type": "system", "content": f"Using tools: {', '.join(tool_names)}"})
        
        return {"messages": [response]}
        
    except Exception as e:
        logger.error(f"Agent node failed: {str(e)}")
        writer({"type": "system", "content": "Error occurred during processing"})
        return state


def should_continue(state: AgentState) -> str:
    """Decide whether to continue to tools or finish."""
    if not state["messages"]:
        return END
    
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END


def create_agent():
    """Create and return the simple ReAct agent."""
    workflow = StateGraph(AgentState)
    
    # Create tool node using LangGraph's built-in ToolNode
    tool_node = ToolNode(AVAILABLE_TOOLS)
    
    # Add nodes
    workflow.add_node("context_preparation", context_preparation_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
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
    """Stream agent tokens - super simple scheme."""
    if agent is None:
        agent = create_agent()
    
    state = {
        "messages": [HumanMessage(content=message)],
        "user_id": None
    }
    
    async for message_chunk, metadata in agent.astream(state, stream_mode="messages"):
        node = metadata.get("langgraph_node")
        
        # Skip system setup
        if node == "context_preparation":
            continue
            
        # Determine chunk type based on content and context
        if node == "agent":
            # If the agent is making tool calls, classify as thinking
            if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
                chunk_type = "thinking"  # Agent reasoning about tools
            else:
                chunk_type = "message"   # Direct response to user
        elif node == "tools":
            chunk_type = "tool"
        else:
            chunk_type = "message"  # Default
        
        # Always yield chunks (even empty ones for thinking)
        yield {
            "type": chunk_type,
            "content": message_chunk.content or ""
        }
    
    # Signal end of stream
    yield {
        "type": "done",
        "content": ""
    }