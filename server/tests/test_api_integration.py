import pytest
import json
import asyncio
import pytest_asyncio
import aiohttp
from typing import Dict, List, Any

# Mark tests as asyncio
pytestmark = [pytest.mark.asyncio]

async def read_sse_stream(response, max_events=10, timeout=5):
    """
    Read and parse events from an SSE stream.
    
    Args:
        response: The HTTP response object with SSE data
        max_events: Maximum number of events to read before stopping
        timeout: Timeout in seconds
        
    Returns:
        List of parsed SSE events
    """
    events = []
    current_event = {'event': None, 'data': '', 'id': None}
    event_count = 0
    
    try:
        # Use iter_any instead of iter_lines since StreamReader doesn't have iter_lines
        buffer = b''
        async for chunk in response.content.iter_chunks():
            if chunk:
                buffer += chunk[0]
                lines = buffer.split(b'\n')
                
                # Process all complete lines
                for i, line_bytes in enumerate(lines[:-1]):
                    line = line_bytes.decode('utf-8')
                    
                    # Debug log
                    print(f"SSE LINE: {line}")
                    
                    # Skip empty lines
                    if not line.strip():
                        # Empty line means the end of an event
                        if current_event['data']:
                            events.append(current_event.copy())
                            current_event = {'event': None, 'data': '', 'id': None}
                            event_count += 1
                            
                            if event_count >= max_events:
                                return events
                        continue
                    
                    # Parse the SSE line
                    if line.startswith('event:'):
                        current_event['event'] = line[6:].strip()
                    elif line.startswith('data:'):
                        current_event['data'] += line[5:].strip()
                    elif line.startswith('id:'):
                        current_event['id'] = line[3:].strip()
                    elif line.startswith(':'):
                        # Comment/heartbeat
                        events.append({'event': 'heartbeat', 'data': line[1:].strip()})
                
                # Keep the incomplete line for next time
                buffer = lines[-1]
                
        # Process any remaining data
        if buffer:
            line = buffer.decode('utf-8')
            if line.strip():
                print(f"SSE LINE (final): {line}")
                if line.startswith('event:'):
                    current_event['event'] = line[6:].strip()
                elif line.startswith('data:'):
                    current_event['data'] += line[5:].strip()
                elif line.startswith('id:'):
                    current_event['id'] = line[3:].strip()
                elif line.startswith(':'):
                    events.append({'event': 'heartbeat', 'data': line[1:].strip()})
        
        # Add the last event if it exists
        if current_event['data']:
            events.append(current_event.copy())
            
    except asyncio.TimeoutError:
        events.append({'event': 'error', 'data': 'Timeout waiting for SSE events'})
    
    return events

@pytest.fixture
def api_url():
    """Return the base URL for API testing."""
    return 'http://localhost:8000'

@pytest.mark.asyncio
async def test_stream_endpoint_get(api_url):
    """Test the GET method of the /stream endpoint."""
    print("\n\nTesting GET to /api/stream...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_url}/api/stream") as response:
            # Check status and headers
            print(f"Response status: {response.status}")
            print(f"Response headers: {response.headers}")
            assert response.status == 200, f"Expected 200 status, got {response.status}"
            assert response.headers['Content-Type'] == 'text/event-stream', \
                f"Expected SSE content type, got {response.headers['Content-Type']}"
            
            # Read SSE events
            events = await read_sse_stream(response)
            
            # Validate event structure
            assert len(events) > 0, "No events received from SSE stream"
            
            # Debug output all events
            print("\nReceived events:")
            for i, event in enumerate(events):
                print(f"Event {i+1}: {event}")
            
            # Check for basic event types we expect
            event_types = [e['event'] for e in events if e.get('event')]
            print(f"\nReceived event types ({len(event_types)}): {event_types}")
            
            # Count occurrences of each event type
            type_counts = {}
            for etype in event_types:
                type_counts[etype] = type_counts.get(etype, 0) + 1
            print(f"Event type counts: {type_counts}")
            
            # Verify at minimum we get a message_start event
            assert 'message_start' in event_types, "No message_start event found in stream"
            
            # Analyze event data in more detail
            print("\n=== DETAILED EVENT ANALYSIS ===")
            for i, event in enumerate(events):
                event_type = event.get('event')
                if not event_type or event_type == 'heartbeat':
                    continue
                
                print(f"\n--- Event {i+1}: {event_type} ---")
                try:
                    if event.get('data'):
                        data = json.loads(event['data'])
                        print(f"Type: {data.get('type')}")
                        
                        # Message_start events
                        if event_type == 'message_start' and 'message' in data:
                            print(f"Message content array: {data['message'].get('content')}")
                        
                        # Content_block_start events
                        if event_type == 'content_block_start' and 'content_block' in data:
                            block = data['content_block']
                            print(f"Content block: type={block.get('type')}, id={block.get('id')}")
                            print(f"Block index: {data.get('index')}")
                        
                        # Content_block_delta events
                        if event_type == 'content_block_delta' and 'delta' in data:
                            delta = data['delta']
                            delta_type = delta.get('type', 'unknown')
                            delta_text = delta.get('text', '')
                            print(f"Delta type: {delta_type}")
                            print(f"Delta text: '{delta_text}'")
                            print(f"Block index: {data.get('index')}")
                        
                        # Message_delta events
                        if event_type == 'message_delta' and 'delta' in data:
                            delta = data['delta']
                            print(f"Stop reason: {delta.get('stop_reason')}")
                            print(f"Stop sequence: {delta.get('stop_sequence')}")
                            if 'usage' in data:
                                print(f"Output tokens: {data['usage'].get('output_tokens')}")
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error parsing event data: {e}")
                    print(f"Raw data: {event.get('data')}")
            
            # Verify event data is valid JSON where applicable
            for event in events:
                if event.get('data') and event['event'] != 'heartbeat':
                    try:
                        json_data = json.loads(event['data'])
                        assert isinstance(json_data, dict), f"Event data is not a JSON object: {json_data}"
                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON in event data: {event['data']}")

@pytest.mark.asyncio
async def test_stream_endpoint_post(api_url):
    """Test the POST method of the /stream endpoint."""
    print("\n\nTesting POST to /api/stream...")
    test_message = "Hello, this is a test message for BookedAI!"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_url}/api/stream",
            json={"message": test_message},
            headers={"Content-Type": "application/json"}
        ) as response:
            # Check status and headers
            print(f"Response status: {response.status}")
            print(f"Response headers: {response.headers}")
            assert response.status == 200, f"Expected 200 status, got {response.status}"
            assert response.headers['Content-Type'] == 'text/event-stream', \
                f"Expected SSE content type, got {response.headers['Content-Type']}"
            
            # Read SSE events
            events = await read_sse_stream(response, max_events=20, timeout=10)
            
            # Debug output all events
            print("\nReceived events:")
            for i, event in enumerate(events):
                print(f"Event {i+1}: {event}")
            
            # Validate event structure 
            assert len(events) > 0, "No events received from SSE stream"
            
            # Check for required Anthropic-style event sequence
            event_types = [e['event'] for e in events if e.get('event')]
            print(f"\nReceived event types ({len(event_types)}): {event_types}")
            
            # Count occurrences of each event type
            type_counts = {}
            for etype in event_types:
                type_counts[etype] = type_counts.get(etype, 0) + 1
            print(f"Event type counts: {type_counts}")
            
            # Basic minimum sequence checks
            assert 'message_start' in event_types, "No message_start event found"
            assert 'content_block_start' in event_types, "No content_block_start event found"
            
            # Analyze content blocks and their types
            content_blocks = []
            for event in events:
                if event.get('event') == 'content_block_start' and event.get('data'):
                    try:
                        data = json.loads(event['data'])
                        if 'content_block' in data:
                            block_type = data['content_block'].get('type')
                            block_id = data['content_block'].get('id')
                            content_blocks.append((block_type, block_id))
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            print(f"\nContent block types: {content_blocks}")
            
            # Analyze event data in more detail
            print("\n=== DETAILED EVENT ANALYSIS ===")
            for i, event in enumerate(events):
                event_type = event.get('event')
                if not event_type or event_type == 'heartbeat':
                    continue
                
                print(f"\n--- Event {i+1}: {event_type} ---")
                try:
                    if event.get('data'):
                        data = json.loads(event['data'])
                        print(f"Type: {data.get('type')}")
                        
                        # Message_start events
                        if event_type == 'message_start' and 'message' in data:
                            print(f"Message content array: {data['message'].get('content')}")
                        
                        # Content_block_start events
                        if event_type == 'content_block_start' and 'content_block' in data:
                            block = data['content_block']
                            print(f"Content block: type={block.get('type')}, id={block.get('id')}")
                            print(f"Block index: {data.get('index')}")
                        
                        # Content_block_delta events
                        if event_type == 'content_block_delta' and 'delta' in data:
                            delta = data['delta']
                            delta_type = delta.get('type', 'unknown')
                            delta_text = delta.get('text', '')
                            print(f"Delta type: {delta_type}")
                            print(f"Delta text: '{delta_text}'")
                            print(f"Block index: {data.get('index')}")
                        
                        # Message_delta events
                        if event_type == 'message_delta' and 'delta' in data:
                            delta = data['delta']
                            print(f"Stop reason: {delta.get('stop_reason')}")
                            print(f"Stop sequence: {delta.get('stop_sequence')}")
                            if 'usage' in data:
                                print(f"Output tokens: {data['usage'].get('output_tokens')}")
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error parsing event data: {e}")
                    print(f"Raw data: {event.get('data')}")
            
            # Check for deltas (actual content)
            delta_events = [e for e in events if e.get('event') == 'content_block_delta']
            assert len(delta_events) > 0, "No content delta events found"
            
            # Parse all delta event data to verify the content is being streamed
            content_fragments = []
            delta_types = set()
            for event in delta_events:
                try:
                    data = json.loads(event['data'])
                    if 'delta' in data:
                        delta = data['delta']
                        delta_type = delta.get('type')
                        if delta_type:
                            delta_types.add(delta_type)
                        
                        if 'text' in delta:
                            content_fragments.append(delta['text'])
                except (json.JSONDecodeError, KeyError):
                    pass
            
            print(f"\nDelta types found: {delta_types}")
            
            # Ensure we got some content
            assert len(content_fragments) > 0, "No content fragments found in delta events"
            combined_content = ''.join(content_fragments)
            print(f"Combined content ({len(combined_content)} chars): {combined_content[:100]}...")
            assert len(combined_content) > 0, "Empty content received" 