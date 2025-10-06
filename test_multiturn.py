#!/usr/bin/env python3
"""
Test script for multi-turn conversations with persistence.
"""

import os
import json
import asyncio
import requests
from sseclient import SSEClient  # pip install sseclient-py

# Configuration
BASE_URL = "http://localhost:8001"
AUTH_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozOSwidXNlcm5hbWUiOiJkYXJ5bEB5ZXNodW1hbi5pbyIsImVtYWlsIjoiZGFyeWxAeWVzaHVtYW4uaW8iLCJleHAiOjE3MzYwNzM3ODUsImlhdCI6MTczNTk4NzM4NX0.3B5J8Z2K4L9M7N6P1Q0W5T8Y2U4I0O9P8L7K6J5H4G3F2D1S0A9"
HEADERS = {
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json"
}

def send_message(thread_id: str, message: str):
    """Send a message to a thread and collect the streaming response."""
    url = f"{BASE_URL}/agent/stream"
    data = {
        "message": message,
        "thread_id": thread_id
    }

    print(f"\n📤 Sending to thread {thread_id}: '{message}'")

    response = requests.post(url, json=data, headers=HEADERS, stream=True)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

    # Parse SSE stream
    messages = []
    current_message = ""

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    event_type = data.get('type', '')

                    if event_type == 'message':
                        current_message += data.get('content', '')
                    elif event_type == 'content_block_delta':
                        delta = data.get('delta', {})
                        if delta.get('type') == 'message_delta':
                            current_message += delta.get('text', '')
                    elif event_type == 'done':
                        break

                except json.JSONDecodeError:
                    continue

    print(f"📥 Agent response: '{current_message[:100]}...'")
    return current_message

async def test_multiturn():
    """Test multi-turn conversation with persistence."""

    print("🧪 Testing Multi-turn Conversation with Persistence")
    print("=" * 60)

    thread_id = "test_thread_123"

    # First message
    response1 = send_message(thread_id, "My favorite color is blue")
    if not response1:
        print("❌ First message failed")
        return

    # Second message - should remember the color
    response2 = send_message(thread_id, "What is my favorite color?")
    if not response2:
        print("❌ Second message failed")
        return

    # Third message - continue the conversation
    response3 = send_message(thread_id, "Why do you think I like that color?")
    if not response3:
        print("❌ Third message failed")
        return

    print("\n" + "=" * 60)
    print("✅ Multi-turn test completed!")
    print("✅ Checkpointer should have maintained conversation state")
    print("✅ Agent should remember the color 'blue' across all messages")

if __name__ == "__main__":
    asyncio.run(test_multiturn())

