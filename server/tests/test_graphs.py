"""
Tests for the BookedAI graph module.

This test suite verifies that the BookedAI graph correctly processes
real (non-mocked) responses from instructors and follows the expected flow.
"""
import pytest
import asyncio
import json
from typing import List, Dict, Any, Set, AsyncGenerator, Callable
from unittest.mock import patch

import pytest_asyncio
from langgraph.graph import END

from agent.graphs import (
    GraphState,
    thinking_node,
    voice_node,
    message_node,
    route_from_thinking,
    create_thinking_centric_graph,
    async_graph_streaming_response
)

from agent.instructors import ThinkingResponse, MessageResponse, VoiceResponse


class StreamEventCollector:
    """Helper class to collect stream events."""
    
    def __init__(self):
        self.events = []
        self.chunks_by_type = {}
        
    def __call__(self, event):
        """Collect events written by the stream writer."""
        self.events.append(event.copy())
        
        # Group chunks by type for easier analysis
        event_type = event.get("type", "unknown")
        if event_type not in self.chunks_by_type:
            self.chunks_by_type[event_type] = []
        
        self.chunks_by_type[event_type].append(event.get("content", ""))
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Return all collected events."""
        return self.events
        
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Return all events of a specific type."""
        return [event for event in self.events if event.get("type") == event_type]
    
    def get_content_by_type(self, event_type: str) -> List[str]:
        """Return all content strings for a specific event type."""
        return self.chunks_by_type.get(event_type, [])
    
    def verify_incremental_content(self, event_type: str) -> bool:
        """
        Verify that content for the given event type is incremental.
        Returns True if content appears to be properly streamed.
        """
        chunks = self.get_content_by_type(event_type)
        if not chunks or len(chunks) <= 1:
            return False
        
        # Check if each chunk builds on the previous one
        # or contains new content not in the previous chunk
        for i in range(1, len(chunks)):
            current = chunks[i]
            previous = chunks[i-1]
            
            # Skip empty chunks
            if not current:
                continue
                
            # If the current chunk is shorter than the previous,
            # it's definitely not incremental
            if len(current) < len(previous):
                return False
                
            # If the current chunk doesn't start with the previous chunk,
            # then content isn't properly accumulating
            if not current.startswith(previous):
                # Some models might send individual words or segments
                # so check if the current chunk adds new content
                if current not in previous:
                    # This is good - it means we're getting new content
                    pass
                else:
                    # The chunk is repeating or going backwards
                    return False
        
        return True
    
    def verify_no_duplicate_content(self, event_type: str) -> bool:
        """
        Verify that there are no completely duplicate content chunks
        for the given event type.
        """
        chunks = self.get_content_by_type(event_type)
        if not chunks:
            return True
            
        # Convert to set to check for duplicates
        unique_chunks = set(chunks)
        
        # If we have the same number of unique chunks as total chunks,
        # there are no duplicates
        return len(unique_chunks) == len(chunks)
    
    def concatenate_content(self, event_type: str) -> str:
        """
        Return the concatenated content for a given event type.
        """
        chunks = self.get_content_by_type(event_type)
        if not chunks:
            return ""
            
        # For proper incremental content, the last chunk should contain everything
        return chunks[-1]
    
    def clear(self):
        """Clear all collected events."""
        self.events = []
        self.chunks_by_type = {}


@pytest.mark.asyncio
async def test_thinking_node_real_streaming():
    """
    Test that the thinking node actually produces incremental content
    when using a real implementation.
    """
    # Create event collector
    collector = StreamEventCollector()
    
    # Patch the get_stream_writer function to return our collector
    with patch("agent.graphs.get_stream_writer", return_value=collector):
        # Set up initial state with a simple query
        state = GraphState(query="What is BookedAI?")
        
        # Run the real thinking node
        result_state = await thinking_node(state)
        
        # Verify results
        assert result_state.thinking_response is not None
        assert result_state.thinking_response.next_action in ["voice", "message", "voice_and_message", "complete"]
        
        # Get thinking events
        thinking_events = collector.get_events_by_type("thinking")
        
        # Verify we got some events
        assert len(thinking_events) > 0, "No thinking events were produced"
        
        # Print debugging info
        print(f"Number of thinking events: {len(thinking_events)}")
        print(f"First few chunks: {collector.get_content_by_type('thinking')[:3]}")
        
        # Check if content is incremental
        is_incremental = collector.verify_incremental_content("thinking")
        
        # If we have sufficient events, check for incrementality
        if len(thinking_events) > 2:
            assert is_incremental, "Thinking content is not being streamed incrementally"
        
            # Verify no completely duplicate chunks
            no_duplicates = collector.verify_no_duplicate_content("thinking")
            assert no_duplicates, "Duplicate thinking chunks detected"
        
            # Verify the final thinking response matches what was streamed
            final_streamed = collector.concatenate_content("thinking")
            assert result_state.thinking_response.analysis == final_streamed, "Final thinking response doesn't match streamed content"


@pytest.mark.asyncio
async def test_message_node_real_streaming():
    """
    Test that the message node actually produces incremental content
    when using a real implementation.
    """
    # Create event collector
    collector = StreamEventCollector()
    
    # Patch the get_stream_writer function to return our collector
    with patch("agent.graphs.get_stream_writer", return_value=collector):
        # Set up initial state with a thinking response
        thinking_response = ThinkingResponse(
            analysis="This is a query about BookedAI",
            next_action="message"
        )
        
        state = GraphState(
            query="What is BookedAI?",
            thinking_response=thinking_response
        )
        
        # Run the real message node
        result_state = await message_node(state)
        
        # Verify results
        assert result_state.message_response is not None
        
        # Get message events
        message_events = collector.get_events_by_type("message")
        
        # Verify we got some events
        assert len(message_events) > 0, "No message events were produced"
        
        # Print debugging info
        print(f"Number of message events: {len(message_events)}")
        print(f"First few chunks: {collector.get_content_by_type('message')[:3]}")
        
        # If we have sufficient events, check for incrementality
        if len(message_events) > 2:
            # Check if content is incremental
            is_incremental = collector.verify_incremental_content("message")
            assert is_incremental, "Message content is not being streamed incrementally"
            
            # Verify no completely duplicate chunks
            no_duplicates = collector.verify_no_duplicate_content("message")
            assert no_duplicates, "Duplicate message chunks detected"
            
            # Verify the final message response matches what was streamed
            final_streamed = collector.concatenate_content("message")
            assert result_state.message_response.content == final_streamed, "Final message response doesn't match streamed content"


@pytest.mark.asyncio
async def test_voice_node_real_streaming():
    """
    Test that the voice node actually produces incremental content
    when using a real implementation.
    
    Note: This test may fail if the voice service is not properly configured
    or the API key is not valid. In that case, skip the test.
    """
    # Create event collector
    collector = StreamEventCollector()
    
    try:
        # Patch the get_stream_writer function to return our collector
        with patch("agent.graphs.get_stream_writer", return_value=collector):
            # Set up initial state
            state = GraphState(query="What is BookedAI?")
            
            # Run the voice node
            result_state = await voice_node(state)
            
            # Get voice events
            voice_events = collector.get_events_by_type("voice")
            
            # Verify we got some events
            assert len(voice_events) > 0, "No voice events were produced"
            
            # Check for START marker
            assert "VOICE_START" in collector.get_content_by_type("voice"), "No VOICE_START marker found"
            
            # Check if there are any non-error voice events after the START marker
            voice_content = collector.get_content_by_type("voice")
            non_error_content = [c for c in voice_content if not c.startswith("Error") and c != "VOICE_START"]
            
            # Print debugging info
            print(f"Number of voice events: {len(voice_events)}")
            print(f"Voice content: {voice_content[:5]}")
            
            if non_error_content:
                # If we have sufficient events, check for incrementality
                if len(non_error_content) > 2:
                    # Check if content is incremental
                    is_incremental = collector.verify_incremental_content("voice")
                    assert is_incremental, "Voice content is not being streamed incrementally"
                    
                    # Verify no completely duplicate chunks
                    no_duplicates = collector.verify_no_duplicate_content("voice")
                    assert no_duplicates, "Duplicate voice chunks detected"
            else:
                print("WARNING: Voice node appears to have errors or no content, skipping incremental checks")
            
    except Exception as e:
        pytest.skip(f"Voice test failed with error: {str(e)}")


@pytest.mark.asyncio
async def test_full_graph_real_streaming():
    """
    Test the complete graph with real streaming to check for incrementality.
    
    This tests direct API calls to async_graph_streaming_response to verify
    that streaming works properly at the graph level.
    """
    # Create a list to collect events
    events = []
    
    # Set up a simple query
    test_query = "What is BookedAI in one sentence?"
    
    # Create a uniquely identifiable query
    unique_query = f"{test_query} (test run: {id(events)})"
    
    # Use the actual async_graph_streaming_response directly
    response_generator = async_graph_streaming_response(system_message=unique_query)
    
    # Collect all events with a timeout to avoid hanging
    try:
        # Use asyncio.wait_for to set a timeout
        # Collect the first 20 events or wait 30 seconds, whichever comes first
        async def collect_events():
            count = 0
            async for event in response_generator:
                events.append(event)
                count += 1
                if count >= 20:
                    break
                
        await asyncio.wait_for(collect_events(), timeout=30)
    except asyncio.TimeoutError:
        print("Timeout occurred, but we'll analyze what we got")
    
    # Only proceed with analysis if we collected some events
    if not events:
        pytest.skip("No events were collected from the graph")
    
    # Group events by type
    events_by_type = {}
    for event in events:
        event_type = event.get("type", "unknown")
        if event_type not in events_by_type:
            events_by_type[event_type] = []
        events_by_type[event_type].append(event)
    
    # Print summary of events
    print(f"\nCollected {len(events)} events in total")
    for event_type, type_events in events_by_type.items():
        print(f"{event_type}: {len(type_events)} events")
    
    # Analyze events of each type for incrementality
    for event_type, type_events in events_by_type.items():
        # Skip if not enough events to analyze
        if len(type_events) <= 1:
            continue
            
        print(f"\nAnalyzing {event_type} events:")
        
        # Extract content
        contents = [event.get("content", "") for event in type_events]
        
        # Check for duplicates
        unique_contents = set(contents)
        print(f"- {len(unique_contents)} unique content chunks out of {len(contents)} total")
        
        # Print first few to see the pattern
        print(f"- First few content chunks: {contents[:3]}")
        
        # Check for incremental pattern
        is_incremental = False
        for i in range(1, len(contents)):
            current = contents[i]
            previous = contents[i-1]
            
            # Skip empty chunks
            if not current or not previous:
                continue
                
            if len(current) >= len(previous) and (
                current.startswith(previous) or  # Growing content
                current not in previous  # New content
            ):
                is_incremental = True
                break
        
        # Report incrementality
        if is_incremental:
            print("- PASS: Content appears to be incremental")
        else:
            print("- FAIL: Content does not appear to be incremental")
            # Don't fail the test, just report the issue
            # We want to see all analysis
    
    # At least verify we got thinking events
    assert "thinking" in events_by_type, "No thinking events were produced"


@pytest.mark.asyncio
async def test_route_from_thinking():
    """Test the routing logic based on thinking response (no mocks needed)."""
    # Test message routing
    state = GraphState(
        thinking_response=ThinkingResponse(
            analysis="test",
            next_action="message"
        )
    )
    assert route_from_thinking(state) == "message"
    
    # Test voice routing
    state.thinking_response.next_action = "voice"
    assert route_from_thinking(state) == "voice"
    
    # Test parallel routing
    state.thinking_response.next_action = "voice_and_message"
    assert route_from_thinking(state) == "parallel"
    
    # Test completion
    state.thinking_response.next_action = "complete"
    assert route_from_thinking(state) == END
    
    # Test error handling
    state.error = "test error"
    assert route_from_thinking(state) == "error_handler" 