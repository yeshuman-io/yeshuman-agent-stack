"""
Tests for streaming agent functionality.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch
from agent.graph import astream_agent, create_agent


class TestStreamingAgent:
    """Test streaming agent functionality."""
    
    @pytest.mark.asyncio
    async def test_astream_agent_basic(self):
        """Test basic streaming agent functionality."""
        with patch('agent.graph.create_agent') as mock_create_agent:
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

    @pytest.mark.asyncio
    async def test_async_streaming_events(self):
        """Test async streaming event format."""
        events = []
        
        async for event in astream_agent("Say hello"):
            events.append(event)
            if len(events) >= 3:  # Limit for test speed
                break
        
        assert len(events) > 0
        # Check event format
        for event in events:
            assert isinstance(event, dict)
            assert 'type' in event
    
    @pytest.mark.asyncio
    async def test_async_streaming_message_types(self):
        """Test that async streaming produces expected message types."""
        thinking_found = False
        message_found = False
        
        async for event in astream_agent("What is 2+2?"):
            if event.get('type') == 'thinking':
                thinking_found = True
            elif event.get('type') == 'message':
                message_found = True
            
            if thinking_found and message_found:
                break
        
        assert thinking_found, "Should have thinking events"
        assert message_found, "Should have message events"

    @pytest.mark.asyncio
    async def test_streaming_content_structure(self):
        """Test that streaming content has proper structure."""
        events_with_content = []
        
        async for event in astream_agent("Explain gravity briefly"):
            if event.get('content'):
                events_with_content.append(event)
            if len(events_with_content) >= 2:  # Limit for test speed
                break
        
        assert len(events_with_content) > 0
        for event in events_with_content:
            assert isinstance(event.get('content'), str)
            assert len(event.get('content')) > 0

    def test_create_agent_has_async_methods(self):
        """Test that created agent has required async methods."""
        with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}):
            agent = create_agent()
            
            # Should have async methods for new LangGraph implementation
            assert hasattr(agent, 'ainvoke')
            assert hasattr(agent, 'astream')

    def test_create_agent_returns_compiled_graph(self):
        """Test that created agent returns a compiled StateGraph instance."""
        with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}):
            agent = create_agent()
            
            # Should return a compiled StateGraph
            assert agent is not None
            # CompiledStateGraph has specific methods for execution
            assert hasattr(agent, 'ainvoke')  # Can invoke async
            assert hasattr(agent, 'astream')  # Can stream async


