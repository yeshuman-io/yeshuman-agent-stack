"""
Tests for the YesHuman agent functionality.
"""
import os
import pytest
from unittest.mock import patch
from agents.agent import invoke_agent, create_agent
from tools.utilities import AVAILABLE_TOOLS


class TestAgent:
    """Test the agent functionality."""
    
    def test_available_tools_exist(self):
        """Test that tools are properly loaded."""
        assert len(AVAILABLE_TOOLS) > 0
        tool_names = [tool.name for tool in AVAILABLE_TOOLS]
        assert "calculator" in tool_names
        assert "echo" in tool_names
    
    def test_create_agent(self):
        """Test agent creation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = create_agent()
            assert agent is not None
    
    def test_invoke_agent_without_api_key(self):
        """Test agent invocation without API key."""
        # Test that create_agent properly validates API key
        with patch.dict(os.environ, {}, clear=True):
            try:
                create_agent()
                assert False, "Should have raised an error"
            except ValueError as e:
                assert "OPENAI_API_KEY" in str(e)
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
    def test_invoke_agent_with_real_key(self):
        """Test agent invocation with real API key."""
        result = invoke_agent("Echo back: test message")
        assert result["success"] is True
        assert "response" in result
        assert len(result["response"]) > 0
    
    def test_calculator_tool_directly(self):
        """Test calculator tool directly."""
        calc_tool = next(tool for tool in AVAILABLE_TOOLS if tool.name == "calculator")
        result = calc_tool._run("2 + 2")
        assert "4" in result
    
    def test_echo_tool_directly(self):
        """Test echo tool directly."""
        echo_tool = next(tool for tool in AVAILABLE_TOOLS if tool.name == "echo")
        result = echo_tool._run("test message")
        assert result == "Echo: test message"
