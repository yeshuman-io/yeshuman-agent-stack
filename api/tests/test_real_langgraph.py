"""
Test real LangGraph implementation with actual LLM calls.
NO MOCKING - this tests real functionality.
"""
import pytest
import asyncio
from agent.graph import create_agent, ainvoke_agent, astream_agent


class TestRealLangGraph:
    """Test the real LangGraph agent with actual LLM calls."""
    
    def test_create_agent(self):
        """Test that we can create the custom LangGraph agent."""
        agent = create_agent()
        assert agent is not None
        # The agent should be a compiled LangGraph
        assert hasattr(agent, 'invoke')
        assert hasattr(agent, 'ainvoke')
        assert hasattr(agent, 'astream')
    
    @pytest.mark.asyncio
    async def test_ainvoke_agent_basic_math(self):
        """Test basic async agent invocation with a simple message."""
        result = await ainvoke_agent("What is 2 + 2?")
        
        assert result["success"] is True
        assert "response" in result
        assert "thinking" in result
        assert len(result["response"]) > 0
        assert len(result["thinking"]) > 0
        
        # Should have both user and AI messages
        assert result["message_count"] == 2
        
        print(f"Thinking: {result['thinking']}")
        print(f"Response: {result['response']}")
    
    @pytest.mark.asyncio
    async def test_ainvoke_agent_basic(self):
        """Test async agent invocation."""
        result = await ainvoke_agent("Hello, who are you?")
        
        assert result["success"] is True
        assert "response" in result
        assert "thinking" in result
        assert len(result["response"]) > 0
        assert len(result["thinking"]) > 0
        
        print(f"Thinking: {result['thinking']}")
        print(f"Response: {result['response']}")
    
    @pytest.mark.asyncio
    async def test_astream_agent_basic(self):
        """Test streaming agent execution."""
        events = []
        
        async for event in astream_agent("Explain why the sky is blue in one sentence."):
            events.append(event)
            print(f"Event: {event}")
        
        assert len(events) > 0
        
        # Should have events from thinking and response nodes
        thinking_events = [e for e in events if e.get('type') == 'thinking']
        response_events = [e for e in events if e.get('type') == 'text']  # Updated to 'text'
        
        assert len(thinking_events) > 0
        assert len(response_events) > 0
    
    @pytest.mark.asyncio
    async def test_agent_with_math_question(self):
        """Test agent with a math question to see thinking process."""
        result = await ainvoke_agent("If I have 5 apples and give away 2, how many do I have left?")
        
        assert result["success"] is True
        
        # The thinking should mention the calculation
        thinking = result["thinking"].lower()
        assert "5" in thinking or "five" in thinking
        assert "2" in thinking or "two" in thinking
        
        # The response should have the correct answer
        response = result["response"].lower()
        assert "3" in response or "three" in response
        
        print(f"Math Thinking: {result['thinking']}")
        print(f"Math Response: {result['response']}")
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Test agent error handling with invalid input."""
        # This should still work - the agent should handle any string input
        result = await ainvoke_agent("")
        
        # Even with empty input, agent should respond gracefully
        assert result["success"] is True
        assert "response" in result
