"""
Tests for the YesHuman agent functionality.
"""
import os
import pytest
from unittest.mock import patch
from agent.graph import ainvoke_agent, create_agent
from tools.utilities import AVAILABLE_TOOLS


class TestAgent:
    """Test the agent functionality."""
    
    def test_available_tools_exist(self):
        """Test that tools are properly loaded."""
        assert len(AVAILABLE_TOOLS) > 0
        tool_names = [tool.name for tool in AVAILABLE_TOOLS]
        assert "calculator" in tool_names
        assert "weather" in tool_names
        assert "text_analysis" in tool_names
        # Echo tool should not be in ReAct agent tools (removed for focused toolset)
        assert "echo" not in tool_names
    
    def test_create_agent(self):
        """Test agent creation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = create_agent()
            assert agent is not None
    
    def test_create_agent_without_api_key(self):
        """Test agent creation without API key."""
        # Test that create_agent succeeds (validation happens at runtime)
        with patch.dict(os.environ, {}, clear=True):
            agent = create_agent()
            # Agent creation should succeed, but using it without API key should fail
            assert agent is not None
            assert hasattr(agent, 'ainvoke')
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
    async def test_ainvoke_agent_with_real_key(self):
        """Test async agent invocation with real API key."""
        result = await ainvoke_agent("Echo back: test message")
        assert result["success"] is True
        assert "response" in result
        assert len(result["response"]) > 0
    
    @pytest.mark.asyncio
    async def test_calculator_tool_directly(self):
        """Test calculator tool directly."""
        calc_tool = next(tool for tool in AVAILABLE_TOOLS if tool.name == "calculator")
        result = await calc_tool._arun("2 + 2")
        assert "4" in result
    
    @pytest.mark.asyncio
    async def test_weather_tool_directly(self):
        """Test weather tool directly."""
        weather_tool = next(tool for tool in AVAILABLE_TOOLS if tool.name == "weather")
        result = await weather_tool._arun("New York")
        assert "New York" in result
        assert "°C" in result or "°F" in result  # Check for temperature symbol
