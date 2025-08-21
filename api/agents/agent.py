"""
YesHuman Agent - Simple functional approach using create_react_agent.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from tools.utilities import AVAILABLE_TOOLS

# Load environment variables
load_dotenv()


# System prompt for the agent
SYSTEM_PROMPT = """You are YesHuman Agent, a helpful AI assistant built on the YesHuman stack.

Your capabilities:
- Use available tools to help users with various tasks
- Provide clear, accurate, and helpful responses
- Be concise but thorough in your explanations
- Always use tools when they would be helpful

Available tools: calculator (for math), echo (for testing)

Be helpful, accurate, and professional in all interactions."""


def create_agent():
    """Create and return a LangGraph agent."""
    # Check for API key first
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=api_key
    )
    
    # Create the agent using LangGraph's prebuilt
    agent = create_react_agent(
        llm,
        AVAILABLE_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT)
    )
    
    return agent


def invoke_agent(message: str, agent=None):
    """Invoke the agent with a message."""
    if agent is None:
        agent = create_agent()
    
    try:
        response = agent.invoke({"messages": [("user", message)]})
        
        # Extract the final message
        final_message = response["messages"][-1]
        
        return {
            "success": True,
            "response": final_message.content,
            "message_count": len(response["messages"])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": f"Sorry, I encountered an error: {str(e)}"
        }


async def ainvoke_agent(message: str, agent=None):
    """Async invoke the agent with a message."""
    if agent is None:
        agent = create_agent()
    
    try:
        response = await agent.ainvoke({"messages": [("user", message)]})
        
        # Extract the final message
        final_message = response["messages"][-1]
        
        return {
            "success": True,
            "response": final_message.content,
            "message_count": len(response["messages"])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": f"Sorry, I encountered an error: {str(e)}"
        }