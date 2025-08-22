"""
YesHuman Agent - Simple functional approach using create_react_agent with streaming support.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from tools.utilities import AVAILABLE_TOOLS
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator

# Load environment variables
load_dotenv()


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler to capture streaming tokens."""
    
    def __init__(self):
        self.tokens = []
        self.current_tool_call = None
        
    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        """Called when the LLM generates a new token."""
        self.tokens.append(token)
        
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        """Called when a tool starts running."""
        tool_name = serialized.get("name", "unknown")
        self.current_tool_call = f"[Using {tool_name} tool...]"
        self.tokens.append(self.current_tool_call)
        
    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes running."""
        self.current_tool_call = None


# System prompt for the agent
SYSTEM_PROMPT = """You are YesHuman Agent, a helpful AI assistant built on the YesHuman stack.

Your capabilities:
- Use available tools to help users with various tasks
- Provide clear, accurate, and helpful responses
- Be concise but thorough in your explanations
- Always use tools when they would be helpful

Available tools: calculator (for math), echo (for testing)

Be helpful, accurate, and professional in all interactions."""


def create_agent(streaming: bool = False):
    """Create and return a LangGraph agent."""
    # Check for API key first
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=api_key,
        streaming=streaming
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


async def astream_agent(message: str) -> AsyncGenerator[str, None]:
    """Stream agent response token by token, grouped into words for better UX."""
    agent = create_agent(streaming=True)
    callback = StreamingCallbackHandler()
    
    try:
        # Run the agent with streaming callback
        response_task = asyncio.create_task(
            agent.ainvoke(
                {"messages": [("user", message)]},
                config={"callbacks": [callback]}
            )
        )
        
        # Stream tokens as they arrive, but group into words
        last_token_count = 0
        word_buffer = ""
        
        while not response_task.done():
            current_token_count = len(callback.tokens)
            if current_token_count > last_token_count:
                # Process new tokens
                for token in callback.tokens[last_token_count:current_token_count]:
                    if token.startswith("[Using") and token.endswith("...]"):
                        # Tool usage - yield immediately
                        if word_buffer.strip():
                            yield word_buffer
                            word_buffer = ""
                        yield token
                    elif token.strip() and not token.isspace():
                        # Regular token - add to word buffer
                        word_buffer += token
                        # Yield when we complete a word (space or punctuation)
                        if token.endswith(" ") or token.endswith(".") or token.endswith(",") or token.endswith("!") or token.endswith("?"):
                            yield word_buffer
                            word_buffer = ""
                    else:
                        # Whitespace or empty - add to buffer
                        word_buffer += token
                
                last_token_count = current_token_count
            
            await asyncio.sleep(0.05)  # Slightly longer delay for word-by-word
        
        # Yield any remaining tokens after task completion
        await response_task  # Ensure task is complete
        current_token_count = len(callback.tokens)
        if current_token_count > last_token_count:
            for token in callback.tokens[last_token_count:]:
                if token.startswith("[Using") and token.endswith("...]"):
                    if word_buffer.strip():
                        yield word_buffer
                        word_buffer = ""
                    yield token
                else:
                    word_buffer += token
        
        # Yield any remaining buffer
        if word_buffer.strip():
            yield word_buffer
                
    except Exception as e:
        yield f"Sorry, I encountered an error: {str(e)}"