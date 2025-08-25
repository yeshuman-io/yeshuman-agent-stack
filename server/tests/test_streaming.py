"""
Tests for streaming behavior in BookedAI.

This test suite focuses specifically on verifying incremental streaming
in the BookedAI node functions.
"""
import pytest
import asyncio
from unittest.mock import patch

from agent.graphs import GraphState, thinking_node
from agent.instructors import ThinkingResponse


class StreamEventCapturer:
    """Captures events from the stream writer for analysis."""
    
    def __init__(self):
        self.events = []
        
    def __call__(self, event):
        """Capture an event from the stream writer."""
        print(f"CAPTURED EVENT: {event}")
        self.events.append(event.copy())
        
    @property
    def content_chunks(self):
        """Extract just the content from thinking events."""
        return [
            event.get("content", "") 
            for event in self.events 
            if event.get("type") == "thinking"
        ]
    
    def print_summary(self):
        """Print a summary of captured events."""
        print(f"\n==== CAPTURED {len(self.events)} EVENTS ====")
        
        thinking_events = [e for e in self.events if e.get("type") == "thinking"]
        print(f"Thinking events: {len(thinking_events)}")
        
        if thinking_events:
            for i, event in enumerate(thinking_events):
                print(f"\nThinking Event #{i+1}:")
                content = event.get("content", "")
                print(f"Length: {len(content)}")
                # Print first 40 chars and last 40 chars
                if len(content) > 80:
                    preview = f"{content[:40]}...{content[-40:]}"
                else:
                    preview = content
                print(f"Content: {preview}")
                
        # Check for incrementality
        chunks = self.content_chunks
        if len(chunks) > 1:
            print("\nIncremental Analysis:")
            is_incremental = False
            repeat_full_content = True
            
            for i in range(1, len(chunks)):
                current = chunks[i]
                previous = chunks[i-1]
                
                if not current.startswith(previous):
                    repeat_full_content = False
                
                if len(current) > len(previous) and current.startswith(previous):
                    is_incremental = True
                    print(f"  Event {i} properly builds on event {i-1}")
                    print(f"  Added: '{current[len(previous):]}'")
                elif current not in previous:
                    is_incremental = True
                    print(f"  Event {i} adds new content not in event {i-1}")
                
            if repeat_full_content:
                print("  ISSUE: Events contain repeated full content instead of incremental updates")
            
            if is_incremental:
                print("  RESULT: Content appears to be properly incremental")
            else:
                print("  RESULT: Content is NOT incremental")


@pytest.mark.asyncio
async def test_direct_streaming_behavior():
    """
    Directly test the streaming behavior of a node function.
    
    This test patches the get_stream_writer function to capture
    events and analyze whether content is being streamed
    incrementally (word by word) or as full content.
    """
    # Create event capturer
    capturer = StreamEventCapturer()
    
    # Patch the get_stream_writer function
    with patch("agent.graphs.get_stream_writer", return_value=capturer):
        # Set up initial state
        state = GraphState(query="What does BookedAI do? Keep it short.")
        
        # Run the thinking node
        result_state = await thinking_node(state)
        
        # Print captured events
        capturer.print_summary()
        
        # Basic verification
        assert result_state.thinking_response is not None
        assert len(capturer.events) > 0, "No events were captured"
        
        # Verify we have thinking events
        thinking_events = [e for e in capturer.events if e.get("type") == "thinking"]
        assert len(thinking_events) > 0, "No thinking events were captured"
        
        # Verify the final thinking response
        final_response = result_state.thinking_response.analysis
        print(f"\nFinal response has {len(final_response)} characters")
        
        # If we have enough events, verify incrementality
        chunks = capturer.content_chunks
        if len(chunks) > 1:
            has_true_incremental = False
            for i in range(1, len(chunks)):
                current = chunks[i]
                previous = chunks[i-1]
                
                # Check if current is truly building on previous
                if (len(current) > len(previous) and 
                    current.startswith(previous) and 
                    len(current) - len(previous) < len(previous)):
                    has_true_incremental = True
                    break
                    
            assert has_true_incremental, "Content is not being streamed incrementally"


if __name__ == "__main__":
    # This allows running the test directly with python
    import asyncio
    asyncio.run(test_direct_streaming_behavior()) 