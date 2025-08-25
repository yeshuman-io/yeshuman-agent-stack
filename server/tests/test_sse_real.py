import pytest
import json
import asyncio
import pytest_asyncio
import os
import time
from typing import Dict, List, Any, AsyncGenerator
from unittest.mock import patch
from dotenv import load_dotenv

from agent.generators import SSEGenerator
from openai import AsyncOpenAI

# Load environment variables from .env
load_dotenv()

# NOT using django_db marker to avoid database issues
# Instead, mark tests explicitly as no database
pytestmark = [pytest.mark.asyncio]

@pytest.mark.asyncio
class TestSSEGeneratorReal:
    """
    Tests that perform real API calls to verify the SSEGenerator against the Anthropic-like spec.
    These tests will use the actual OpenAI API, so they require an API key.
    """
    
    @pytest_asyncio.fixture
    async def sse_generator(self):
        """Create an SSEGenerator instance."""
        return SSEGenerator()
    
    @pytest_asyncio.fixture
    async def openai_client(self):
        """Create an AsyncOpenAI client with the API key from environment."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set in environment")
        return AsyncOpenAI(api_key=api_key)
    
    async def create_text_completion_stream(self, client: AsyncOpenAI) -> AsyncGenerator[Dict[str, Any], None]:
        """Create a real stream from OpenAI API with a simple text completion."""
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "What is the capital of France? Respond in one word."}],
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield {"type": "message", "content": content}
            
            # Signal completion
            yield {"type": "done"}
        except Exception as e:
            print(f"Error: {str(e)}")
            yield {"type": "error", "content": f"Error: {str(e)}"}
    
    async def create_function_calling_stream(self, client: AsyncOpenAI) -> AsyncGenerator[Dict[str, Any], None]:
        """Create a real stream from OpenAI API with function calling."""
        try:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather in a given location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state, e.g. San Francisco, CA"
                                },
                                "unit": {
                                    "type": "string",
                                    "enum": ["celsius", "fahrenheit"],
                                    "description": "The unit of temperature to use"
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }
            ]
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using more widely available model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always uses tools when asked about weather."},
                    {"role": "user", "content": "What's the weather like in New York?"}
                ],
                tools=tools,
                tool_choice="auto",
                stream=True
            )
            
            # Track function calling state
            in_tool_call = False
            tool_name = None
            tool_args = ""
            
            async for chunk in response:
                # Check for tool calls (function calls)
                if (hasattr(chunk.choices[0], 'delta') and 
                    hasattr(chunk.choices[0].delta, 'tool_calls') and 
                    chunk.choices[0].delta.tool_calls):
                    
                    tool_calls = chunk.choices[0].delta.tool_calls
                    for tool_call in tool_calls:
                        # Handle index info
                        if hasattr(tool_call, 'index'):
                            print(f"Tool call index: {tool_call.index}")
                            in_tool_call = True
                        
                        # Handle function name
                        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'name'):
                            tool_name = tool_call.function.name
                            print(f"Detected tool name: {tool_name}")
                            yield {
                                "type": "tool_use", 
                                "name": tool_name,
                                "input": {}
                            }
                        
                        # Handle function arguments
                        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                            if tool_call.function.arguments:
                                tool_args += tool_call.function.arguments
                                # Print arguments for debugging
                                print(f"Tool arguments: {tool_call.function.arguments}")
                                # Convert to BookedAI format - fragment by fragment
                                yield {
                                    "type": "tool_input_fragment", 
                                    "name": tool_name, 
                                    "content": tool_call.function.arguments
                                }
                
                # Handle regular content
                elif chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield {"type": "message", "content": content}
            
            # If we collected a tool call, finalize it
            if in_tool_call and tool_name:
                print(f"Final tool args: {tool_args}")
                yield {
                    "type": "tool_input_fragment", 
                    "name": tool_name, 
                    "content": "", 
                    "is_last": True
                }
            
            # Signal completion
            yield {"type": "done"}
        except Exception as e:
            print(f"Error in function calling: {str(e)}")
            yield {"type": "error", "content": f"Error: {str(e)}"}
    
    @pytest.mark.asyncio
    async def test_real_text_completion(self, sse_generator, openai_client):
        """
        Test the SSE generator with a real text completion.
        
        This test makes a real API call to OpenAI with a simple text query about
        the capital of France, collects all SSE events, and ensures the response
        follows the correct event sequence and contains the expected content.
        
        Args:
            sse_generator: The SSEGenerator instance.
            openai_client: The AsyncOpenAI client.
        """
        print("\n\nTesting real text completion...")
        # Collect all the events
        events = []
        async for event in sse_generator.generate_sse(self.create_text_completion_stream(openai_client)):
            event_str = event.decode('utf-8')
            events.append(event_str)
            print(event_str)
        
        # Basic validation - ensure we get the right event types
        assert any("message_start" in e for e in events), "No message_start event"
        assert any("content_block_start" in e for e in events), "No content_block_start event"
        assert any("content_block_delta" in e for e in events), "No content_block_delta event"
        assert any("content_block_stop" in e for e in events), "No content_block_stop event"
        assert any("message_delta" in e for e in events), "No message_delta event"
        assert any("message_stop" in e for e in events), "No message_stop event"
        
        # Also check for specific content
        text_content = ""
        for event in events:
            if "content_block_delta" in event:
                data_line = [line for line in event.split("\n") if line.startswith("data: ")][0]
                data = json.loads(data_line.replace("data: ", ""))
                if "delta" in data and "type" in data["delta"] and data["delta"]["type"] == "text_delta":
                    text_content += data["delta"].get("text", "")
        
        print(f"Extracted text content: {text_content}")
        
        # Check if we really got a response - it should contain "Paris" for our capital of France query
        lowercase_content = text_content.lower()
        assert "paris" in lowercase_content, f"Expected 'Paris' in response but got: {text_content}"