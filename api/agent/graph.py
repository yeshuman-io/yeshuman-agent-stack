"""
YesHuman Agent - Custom LangGraph implementation with parallel thinking and response nodes.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from tools.utilities import AVAILABLE_TOOLS
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator, TypedDict

# Load environment variables
load_dotenv()


# State definition for our custom LangGraph
class AgentState(TypedDict):
    """State for the YesHuman agent graph."""
    messages: List[Any]  # Chat messages
    thinking: str        # Internal reasoning
    final_response: str  # Response to user
    user_message: str    # Current user input


# System prompts for different nodes
THINKING_PROMPT = """You are the thinking component of YesHuman Agent. 
Your job is to analyze the user's message and think through your approach.

User message: {user_message}

Provide your internal reasoning and thought process. Be thorough but concise.
Think about:
- What the user is asking for
- What tools might be needed
- How to structure your response
- Any edge cases or considerations

Your thinking:"""

RESPONSE_PROMPT = """You are YesHuman Agent, a helpful AI assistant.

User message: {user_message}
Your thinking: {thinking}

Based on your thinking process above, provide a helpful response to the user.
Use tools when appropriate. Be clear, accurate, and professional.

Response:"""


# Node functions for our custom LangGraph
async def thinking_node(state: AgentState) -> AgentState:
    """Node that generates internal thinking/reasoning."""
    # Get LLM instance
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=api_key
    )
    
    # Create thinking prompt
    thinking_input = THINKING_PROMPT.format(user_message=state["user_message"])
    
    # Call LLM for thinking (async)
    response = await llm.ainvoke([HumanMessage(content=thinking_input)])
    
    # Update state
    state["thinking"] = response.content
    return state


async def response_node(state: AgentState) -> AgentState:
    """Node that generates the final response to user."""
    # Get LLM instance
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=api_key
    )
    
    # Create response prompt with thinking context
    response_input = RESPONSE_PROMPT.format(
        user_message=state["user_message"],
        thinking=state["thinking"]
    )
    
    # Call LLM for final response (async)
    response = await llm.ainvoke([HumanMessage(content=response_input)])
    
    # Update state
    state["final_response"] = response.content
    state["messages"] = state.get("messages", []) + [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=response.content)
    ]
    
    return state


def create_agent():
    """Create and return a custom LangGraph agent with thinking and response nodes."""
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("thinking", thinking_node)
    workflow.add_node("response", response_node)
    
    # Add edges
    workflow.set_entry_point("thinking")
    workflow.add_edge("thinking", "response")
    workflow.add_edge("response", END)
    
    # Compile the graph
    agent = workflow.compile()
    return agent


# Note: All agent functions are async-only. Use ainvoke_agent() instead of invoke_agent().


async def ainvoke_agent(message: str, agent=None):
    """Async invoke the agent with a message."""
    if agent is None:
        agent = create_agent()
    
    try:
        # Create initial state
        initial_state = {
            "user_message": message,
            "messages": [],
            "thinking": "",
            "final_response": ""
        }
        
        # Run the agent
        result = await agent.ainvoke(initial_state)
        
        return {
            "success": True,
            "response": result["final_response"],
            "thinking": result["thinking"],
            "message_count": len(result["messages"])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": f"Sorry, I encountered an error: {str(e)}"
        }


async def astream_agent(message: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream agent execution, yielding events in SSE format."""
    agent = create_agent()
    
    try:
        # Create initial state
        initial_state = {
            "user_message": message,
            "messages": [],
            "thinking": "",
            "final_response": ""
        }
        
        # Stream the agent execution and convert to SSE format
        async for event in agent.astream(initial_state):
            # Convert LangGraph events to SSE format (type + content)
            if 'thinking' in event:
                thinking_content = event['thinking'].get('thinking', '')
                if thinking_content:
                    yield {
                        'type': 'thinking',
                        'content': thinking_content
                    }
            
            if 'response' in event:
                response_content = event['response'].get('final_response', '')
                if response_content:
                    yield {
                        'type': 'message',  # SSE generator maps 'message' -> 'text_delta'
                        'content': response_content
                    }
        
        # Send completion signal
        yield {'type': 'done', 'content': ''}
                
    except Exception as e:
        yield {"type": "error", "content": str(e)}

