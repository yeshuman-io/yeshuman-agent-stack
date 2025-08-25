"""
Test suite for the instructor implementations.
Focuses on verifying structured output handling and streaming behavior.
"""
import pytest
import pytest_asyncio
import asyncio
from typing import List
from unittest.mock import AsyncMock, patch, MagicMock
from agent.instructors import (
    ThinkingInstructor,
    MessageInstructor,
    VoiceInstructor,
    ThinkingResponse,
    MessageResponse,
    VoiceResponse
)


@pytest_asyncio.fixture
async def thinking_instructor() -> ThinkingInstructor:
    """Fixture providing a ThinkingInstructor instance."""
    instructor = ThinkingInstructor()
    yield instructor


@pytest_asyncio.fixture
async def message_instructor() -> MessageInstructor:
    """Fixture providing a MessageInstructor instance."""
    instructor = MessageInstructor()
    yield instructor


@pytest_asyncio.fixture
async def voice_instructor() -> VoiceInstructor:
    """Fixture providing a VoiceInstructor instance."""
    instructor = VoiceInstructor()
    yield instructor


@pytest.mark.asyncio
async def test_thinking_instructor_structured_output(thinking_instructor: ThinkingInstructor):
    """Test that ThinkingInstructor returns properly structured ThinkingResponse objects."""
    query = "What are the key principles of machine learning?"
    
    # Collect all chunks
    chunks: List[ThinkingResponse] = []
    async for chunk in thinking_instructor.generate(query):
        assert isinstance(chunk, ThinkingResponse)
        chunks.append(chunk)
    
    # Verify we got at least one chunk
    assert len(chunks) > 0
    
    # Verify the last chunk has content
    last_chunk = chunks[-1]
    assert last_chunk.analysis
    assert last_chunk.next_action in ["voice", "message", "voice_and_message", "complete"]


@pytest.mark.asyncio
async def test_message_instructor_structured_output(message_instructor: MessageInstructor):
    """Test that MessageInstructor returns properly structured MessageResponse objects."""
    query = "Explain quantum computing in simple terms."
    
    # Collect all chunks
    chunks: List[MessageResponse] = []
    async for chunk in message_instructor.generate(query):
        assert isinstance(chunk, MessageResponse)
        chunks.append(chunk)
    
    # Verify we got at least one chunk
    assert len(chunks) > 0
    
    # Verify the last chunk has content
    last_chunk = chunks[-1]
    assert last_chunk.content


@pytest.mark.asyncio
async def test_voice_instructor_structured_output(voice_instructor: VoiceInstructor):
    """Test that VoiceInstructor returns properly structured VoiceResponse objects."""
    query = "Create a short voice response about artificial intelligence."
    
    # Collect all chunks
    chunks: List[VoiceResponse] = []
    async for chunk in voice_instructor.generate(query):
        assert isinstance(chunk, VoiceResponse)
        chunks.append(chunk)
    
    # Verify we got at least one chunk
    assert len(chunks) > 0
    
    # Verify the last chunk has content
    last_chunk = chunks[-1]
    assert last_chunk.text


@pytest.mark.asyncio
async def test_instructor_factory():
    """Test the create_instructor factory function."""
    from agent.instructors import create_instructor
    
    # Test creating each type of instructor
    thinking = create_instructor("thinking")
    assert isinstance(thinking, ThinkingInstructor)
    
    message = create_instructor("message")
    assert isinstance(message, MessageInstructor)
    
    voice = create_instructor("voice")
    assert isinstance(voice, VoiceInstructor)
    
    # Test invalid type
    with pytest.raises(ValueError):
        create_instructor("invalid")


@pytest.mark.asyncio
async def test_thinking_instructor_error_handling(thinking_instructor: ThinkingInstructor):
    """Test error handling in ThinkingInstructor."""
    # Create a properly configured AsyncMock
    async_mock = AsyncMock()
    async_mock.side_effect = Exception("API Error")
    
    # Mock the client's create method to simulate an error
    with patch.object(thinking_instructor.client.chat.completions, 'create', async_mock):
        # Should still return a ThinkingResponse with error info
        chunks = []
        async for chunk in thinking_instructor.generate("test query"):
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert isinstance(chunks[0], ThinkingResponse)
        assert "Error" in chunks[0].analysis
        assert chunks[0].next_action == "complete"


@pytest.mark.asyncio
async def test_message_instructor_error_handling(message_instructor: MessageInstructor):
    """Test error handling in MessageInstructor."""
    # Set up a nested AsyncMock to simulate the Anthropic client behavior
    # First level is the coroutine returned by create_partial
    mock_stream = AsyncMock()
    # Second level mock is the iterator that will be awaited
    mock_stream.__aiter__.side_effect = Exception("API Error")
    
    # Create a mock that returns a coroutine that will return our stream
    create_partial_mock = AsyncMock()
    create_partial_mock.return_value = mock_stream
    
    # Mock the client's create_partial method to simulate an error
    with patch.object(message_instructor.client.messages, 'create_partial', create_partial_mock):
        # Should return multiple chunks to simulate streaming
        chunks = []
        async for chunk in message_instructor.generate("test query"):
            chunks.append(chunk)
        
        assert len(chunks) == 2  # Now expecting 2 chunks for error handling
        assert isinstance(chunks[0], MessageResponse)
        assert isinstance(chunks[1], MessageResponse)
        assert "Error" in chunks[0].content
        assert "API Error" in chunks[1].content


@pytest.mark.asyncio
async def test_voice_instructor_error_handling(voice_instructor: VoiceInstructor):
    """Test error handling in VoiceInstructor."""
    # Create a properly configured AsyncMock
    async_mock = AsyncMock()
    async_mock.side_effect = Exception("API Error")
    
    # Mock the client's create method to simulate an error
    with patch.object(voice_instructor.client.chat.completions, 'create', async_mock):
        # Should return multiple chunks to simulate streaming
        chunks = []
        async for chunk in voice_instructor.generate("test query"):
            chunks.append(chunk)
        
        assert len(chunks) == 2  # Now expecting 2 chunks for error handling
        assert isinstance(chunks[0], VoiceResponse)
        assert isinstance(chunks[1], VoiceResponse)
        assert "Error" in chunks[0].text
        assert "API Error" in chunks[1].text


@pytest.mark.asyncio
async def test_thinking_instructor_streaming_behavior(thinking_instructor: ThinkingInstructor):
    """Test streaming behavior of ThinkingInstructor."""
    query = "What are the key principles of machine learning? Provide a concise answer."
    
    # Collect chunks with timestamps
    chunks = []
    timestamps = []
    analysis_lengths = []
    
    async for chunk in thinking_instructor.generate(query):
        chunks.append(chunk)
        timestamps.append(asyncio.get_event_loop().time())
        analysis_lengths.append(len(chunk.analysis))
    
    # Verify we got at least one chunk
    assert len(chunks) > 0
    
    # If we got multiple chunks, verify they show progression
    if len(chunks) > 1:
        # Verify chunks are received in sequence
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1]
        
        # In most cases (not guaranteed), later chunks should have more content
        # as the thinking progresses
        increasing_content = False
        for i in range(1, len(analysis_lengths)):
            if analysis_lengths[i] > analysis_lengths[i-1]:
                increasing_content = True
                break
        
        assert increasing_content, "Expected at least some chunks to show increasing content length"
    
    # Verify final response has meaningful content and a next_action
    assert len(chunks[-1].analysis) > 10  # Arbitrary minimum length
    assert chunks[-1].next_action in ["voice", "message", "voice_and_message", "complete"]


@pytest.mark.asyncio
async def test_message_instructor_streaming_behavior(message_instructor: MessageInstructor):
    """Test streaming behavior of MessageInstructor."""
    query = "Explain quantum computing in simple terms."
    
    # Collect chunks with timestamps
    chunks = []
    timestamps = []
    
    async for chunk in message_instructor.generate(query):
        chunks.append(chunk)
        timestamps.append(asyncio.get_event_loop().time())
    
    # Verify we got at least one chunk
    assert len(chunks) > 0
    
    # If we got multiple chunks, verify they are received in sequence
    if len(chunks) > 1:
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1]
    
    # Verify final response has meaningful content
    assert len(chunks[-1].content) > 10  # Arbitrary minimum length


@pytest.mark.asyncio
async def test_voice_instructor_streaming_behavior(voice_instructor: VoiceInstructor):
    """Test streaming behavior of VoiceInstructor."""
    query = "Create a short voice response about artificial intelligence."
    
    # Collect chunks with timestamps
    chunks = []
    timestamps = []
    
    async for chunk in voice_instructor.generate(query):
        chunks.append(chunk)
        timestamps.append(asyncio.get_event_loop().time())
    
    # Verify we got at least one chunk
    assert len(chunks) > 0
    
    # If we got multiple chunks, verify they are received in sequence
    if len(chunks) > 1:
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1]
    
    # Verify final response has meaningful content
    assert len(chunks[-1].text) > 10  # Arbitrary minimum length 