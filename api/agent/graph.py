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
                # Find the last human message for voice generation context
                user_message = ""
                for msg in reversed(state["messages"]):
                    if isinstance(msg, HumanMessage):
                        user_message = msg.content
                        break
                logger.debug(f"User message for voice: {user_message}")
                
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
        
        # Debug: log the messages being sent to the LLM and available tools
        logger.debug(f"Messages being sent to LLM: {len(state['messages'])} messages")
        for i, msg in enumerate(state["messages"]):
            logger.debug(f"Message {i}: {type(msg).__name__} - {msg.content[:100]}...")
        logger.debug(f"Available tools: {[tool.name for tool in AVAILABLE_TOOLS]}")
        
        # Stream the response token by token
        accumulated_content = ""
        accumulated_tool_calls = []
        final_response = None
        
        async for chunk in llm_with_tools.astream(state["messages"]):
            # Stream content tokens as they arrive
            if chunk.content:
                accumulated_content += chunk.content
                if writer:
                    writer({"type": "message", "content": chunk.content})
            
            # Handle tool calls in streaming - accumulate them
            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                logger.debug(f"Received tool calls in chunk: {chunk.tool_calls}")
                for tc in chunk.tool_calls:
                    logger.debug(f"Tool call details: {tc}")
                    # Only add valid tool calls (with name and id)
                    if tc.get('name') and tc.get('id'):
                        # Check if weather tool has location argument
                        if tc.get('name') == 'weather' and not tc.get('args', {}).get('location'):
                            logger.debug(f"Weather tool call missing location, adding Melbourne as default")
                            tc['args'] = {'location': 'Melbourne'}
                        accumulated_tool_calls.append(tc)
                    else:
                        logger.debug(f"Skipping invalid tool call: {tc}")
            
            final_response = chunk
        
        logger.debug(f"FINAL RESPONSE: {final_response}")
        logger.debug(f"ACCUMULATED CONTENT: '{accumulated_content}'")
        
        # Ensure the response contains the accumulated content and tool calls
        if final_response:
            from langchain_core.messages import AIMessage
            # Use accumulated tool calls if we found any, otherwise use final response's tool calls
            tool_calls = accumulated_tool_calls if accumulated_tool_calls else getattr(final_response, 'tool_calls', [])
            
            response = AIMessage(
                content=accumulated_content,
                additional_kwargs=getattr(final_response, 'additional_kwargs', {}),
                response_metadata=getattr(final_response, 'response_metadata', {}),
                id=getattr(final_response, 'id', None),
                tool_calls=tool_calls
            )
            
            logger.debug(f"ACCUMULATED TOOL CALLS: {accumulated_tool_calls}")
        else:
            response = final_response
        
        # Show tool calls if present
        tool_calls = getattr(response, 'tool_calls', None) or []
        logger.debug(f"Response tool_calls: {tool_calls}")
        logger.debug(f"Response additional_kwargs: {getattr(response, 'additional_kwargs', {})}")
        
        if writer and tool_calls:
            tool_names = [tc.get("name", "unknown") for tc in tool_calls]
            logger.info(f"EMITTING TOOL DELTA: Calling tools: {tool_names}")
            writer({"type": "tool", "content": f"🔧 Calling tools: {', '.join(tool_names)}"})
        else:
            logger.info(f"NO TOOL CALLS - writer: {writer is not None}, tool_calls: {tool_calls}")
            # If we have content but no tool calls, make sure content is streamed
            if accumulated_content.strip() and not tool_calls:
                logger.info(f"Response has content but no tool calls, content length: {len(accumulated_content)}")
            elif not accumulated_content.strip() and not tool_calls:
                logger.warning("Response has no content and no tool calls - this may indicate an issue")
        
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