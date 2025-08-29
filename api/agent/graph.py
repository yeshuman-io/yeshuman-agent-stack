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


async def context_preparation_node(state: AgentState) -> AgentState:
    """Add system prompt to start conversation."""
    # Add system message if not already present
    if not state["messages"] or not isinstance(state["messages"][0], SystemMessage):
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        return {"messages": [system_message]}
    
    return state


async def agent_node(state: AgentState) -> AgentState:
    """Two-stage agent: voice encouragement then main response."""
    writer = get_stream_writer()
    
    # Get LLM instance
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not configured")
        writer({"type": "system", "content": "Configuration error occurred"})
        return state
    
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=1,
        api_key=api_key,
        streaming=True
    )
    
    try:
        logger.info("Agent node started")
        
        # Fire voice generation immediately (don't wait)
        async def generate_voice():
            try:
                logger.info("Starting voice generation")
                user_message = state["messages"][-1].content if state["messages"] else ""
                logger.debug(f"User message: {user_message}")
                
                voice_prompt = f"""
Generate a brief, 2-10 words, contextually appropriate message to let the user know you're working on their request: "{user_message}"
"""
                
                logger.debug("Calling voice LLM...")
                logger.debug(f"VOICE PROMPT: {voice_prompt}")
                
                # Stream voice response token by token
                voice_content = ""
                async for chunk in llm.astream([HumanMessage(content=voice_prompt)]):
                    if chunk.content:
                        voice_content += chunk.content
                        writer({"type": "voice", "content": chunk.content})
                
                logger.info(f"Generated voice message: '{voice_content.strip()}'")
                logger.info("Voice message streamed successfully")
                
            except Exception as e:
                logger.error(f"Voice generation failed: {e}")
        
        # Fire and forget voice generation
        logger.info("Launching voice task")
        import asyncio
        asyncio.create_task(generate_voice())
        
        # Simple agent response - bind tools and stream
        llm_with_tools = llm.bind_tools(AVAILABLE_TOOLS)
        
        # Stream the response token by token
        accumulated_content = ""
        final_response = None
        
        async for chunk in llm_with_tools.astream(state["messages"]):
            # Stream content tokens as they arrive
            if chunk.content:
                accumulated_content += chunk.content
                if writer:
                    writer({"type": "message", "content": chunk.content})
            
            final_response = chunk
        
        logger.debug(f"FINAL RESPONSE: {final_response}")
        response = final_response
        
        # Show tool calls if present
        if writer and hasattr(response, 'tool_calls') and response.tool_calls:
            tool_names = [tc.get("name", "unknown") for tc in response.tool_calls]
            logger.info(f"EMITTING TOOL DELTA: Calling tools: {tool_names}")
            writer({"type": "tool", "content": f"🔧 Calling tools: {', '.join(tool_names)}"})
        else:
            logger.info(f"NO TOOL CALLS - writer: {writer is not None}, tool_calls: {hasattr(response, 'tool_calls') and response.tool_calls}")
        
        logger.info("Agent response completed")
        return {"messages": [response], "writer": writer}
        
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
    
    last_message = state["messages"][-1]
    logger.debug(f"Last message type: {type(last_message).__name__}")
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"Tool calls found: {[tc.get('name', 'unknown') for tc in last_message.tool_calls]}")
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
            if hasattr(last_message, 'tool_calls'):
                logger.info(f"Processing {len(last_message.tool_calls)} tool calls")
        
        result = base_tool_node.invoke(state)
        
        # Show tool results
        if writer and result.get('messages'):
            logger.info(f"CHECKING TOOL RESULTS - writer: {writer is not None}, messages: {len(result.get('messages', []))}")
            new_messages = result['messages'][len(state.get('messages', [])):]
            logger.info(f"NEW MESSAGES COUNT: {len(new_messages)}")
            for i, msg in enumerate(new_messages):
                if hasattr(msg, 'content') and msg.content:
                    # Truncate long results for display
                    content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    logger.info(f"EMITTING SYSTEM DELTA {i}: Tool result: {content[:50]}...")
                    writer({"type": "system", "content": f"✅ Tool result: {content}"})
                else:
                    logger.info(f"MESSAGE {i} HAS NO CONTENT: {type(msg)}")
        else:
            logger.info(f"NO TOOL RESULTS TO SHOW - writer: {writer is not None}, result messages: {result.get('messages', 'None')}")
        
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