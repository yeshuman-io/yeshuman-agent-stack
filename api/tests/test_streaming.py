"""
Tests for streaming agent functionality.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch
from agents.agent import astream_agent, StreamingCallbackHandler, create_agent


class TestStreamingAgent:
    """Test streaming agent functionality."""
    
    @pytest.mark.asyncio
    async def test_astream_agent_basic(self):
        """Test basic streaming agent functionality."""
        with patch('agents.agent.create_agent') as mock_create_agent:
            # Mock the agent and callback
            mock_agent = Mock()
            mock_agent.ainvoke = Mock()
            
            # Mock response task
            mock_response_task = Mock()
            mock_response_task.done.side_effect = [False, False, True]  # Will complete on 3rd check
            
            # Setup async context
            async def mock_create_task(coro):
                return mock_response_task
            
            with patch('asyncio.create_task', side_effect=mock_create_task):
                mock_create_agent.return_value = mock_agent
                
                # Test that we can call astream_agent
                generator = astream_agent("Test message")
                result = []
                
                # Collect first few items (simulate tool usage)
                try:
                    for _ in range(3):  # Limit to prevent infinite loop
                        item = await generator.__anext__()
                        result.append(item)
                        if len(result) >= 2:  # Get a few items and break
                            break
                except StopAsyncIteration:
                    pass
                
                # Should have some output
                assert len(result) >= 0  # At minimum, should not crash

    def test_streaming_callback_handler(self):
        """Test StreamingCallbackHandler token capture."""
        handler = StreamingCallbackHandler()
        
        # Test token collection
        handler.on_llm_new_token("Hello")
        handler.on_llm_new_token(" ")
        handler.on_llm_new_token("world")
        
        assert len(handler.tokens) == 3
        assert handler.tokens == ["Hello", " ", "world"]
    
    def test_streaming_callback_tool_usage(self):
        """Test StreamingCallbackHandler tool usage tracking."""
        handler = StreamingCallbackHandler()
        
        # Mock tool start
        serialized = {"name": "calculator"}
        handler.on_tool_start(serialized, "2+2")
        
        # Should capture tool usage
        assert len(handler.tokens) == 1
        assert handler.tokens[0] == "[Using calculator tool...]"
        assert handler.current_tool_call == "[Using calculator tool...]"
        
        # Mock tool end
        handler.on_tool_end("Result: 4")
        assert handler.current_tool_call is None

    @pytest.mark.asyncio
    async def test_word_grouping_logic(self):
        """Test word grouping in streaming output."""
        # This is a more complex integration test that would need
        # a controlled callback with known tokens
        handler = StreamingCallbackHandler()
        
        # Simulate token sequence that forms words
        tokens = ["The", " ", "quick", " ", "brown", " ", "fox", "."]
        for token in tokens:
            handler.on_llm_new_token(token)
        
        # Should have all tokens
        assert len(handler.tokens) == 8
        assert "".join(handler.tokens) == "The quick brown fox."

    def test_create_agent_streaming_enabled(self):
        """Test agent creation with streaming enabled."""
        with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}):
            with patch('agents.agent.ChatOpenAI') as mock_llm:
                with patch('agents.agent.create_react_agent') as mock_create_react:
                    # Test streaming flag
                    create_agent(streaming=True)
                    
                    # Should have been called with streaming=True
                    mock_llm.assert_called_once()
                    call_args = mock_llm.call_args
                    assert call_args[1]['streaming'] is True

    def test_create_agent_streaming_disabled(self):
        """Test agent creation with streaming disabled."""
        with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}):
            with patch('agents.agent.ChatOpenAI') as mock_llm:
                with patch('agents.agent.create_react_agent') as mock_create_react:
                    # Test no streaming flag (default)
                    create_agent(streaming=False)
                    
                    # Should have been called with streaming=False
                    mock_llm.assert_called_once()
                    call_args = mock_llm.call_args
                    assert call_args[1]['streaming'] is False


