#!/usr/bin/env python3
"""
Simple script to test agent interaction via API endpoints.
Tests authentication, agent streaming, and tool usage.
"""
import json
import requests
import re

def login_and_get_token():
    """Login and get JWT token for authenticated requests."""
    login_url = "http://localhost:8001/api/accounts/login"
    login_data = {
        "username": "daryl",
        "password": "abc"
    }

    print("🔐 Logging in user 'daryl'...")
    response = requests.post(login_url, json=login_data)

    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            token = data["token"]
            print(f"✅ Login successful! Token: {token[:50]}...")
            return token
        else:
            print(f"❌ Login failed: {data}")
            return None
    else:
        print(f"❌ Login request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_agent_streaming(token):
    """Test agent streaming with a simple message."""
    stream_url = "http://localhost:8001/agent/stream"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Test message that should trigger multiple tools - explicit tool requests
    message_data = {
        "message": "Please call the list_opportunities tool and then the list_profiles tool to show me the current data."
    }

    print("\n🤖 Sending message to agent...")
    print(f"Message: {message_data['message']}")
    print(f"URL: {stream_url}")
    print(f"Headers: {headers}")
    print("\n📡 Agent Response:")

    try:
        # Send the request
        response = requests.post(stream_url, json=message_data, headers=headers, stream=True)

        if response.status_code == 200:
            print("✅ Agent streaming started successfully!")
            print("=" * 50)

            # Parse SSE stream manually
            accumulated_response = ""

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()

                    # Parse SSE format: "event: type\ndata: json\n\n"
                    if line_str.startswith('event: '):
                        event_type = line_str[7:]  # Remove 'event: '

                    elif line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: '

                        try:
                            event_data = json.loads(data_str)
                            event_actual_type = event_data.get("type", event_type)

                            if event_type == "error":
                                print(f"❌ Agent Error: {event_data.get('content', data_str)}")
                                break

                            elif event_actual_type == "content_block_delta":
                                delta = event_data.get("delta", {})
                                if isinstance(delta, dict) and "text" in delta:
                                    text = delta["text"]
                                    print(text, end="", flush=True)
                                    accumulated_response += text

                            elif event_actual_type == "message":
                                content = event_data.get("content", "")
                                if content:
                                    print(f"\n📝 Message: {content}")
                                    accumulated_response += content

                            elif event_actual_type == "completion":
                                print(f"\n🏁 Completion: {event_data}")
                                break

                            elif event_type == "done":
                                print("\n🎉 Stream completed!")
                                break

                        except json.JSONDecodeError:
                            print(f"Raw event: {event_type} - {data_str}")

        else:
            print(f"❌ Agent request failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error communicating with agent: {str(e)}")
        import traceback
        traceback.print_exc()

def test_focus_api(token):
    """Test the focus API endpoints."""
    print("\n🎯 Testing Focus API")

    # Test GET /api/accounts/focus
    focus_url = "http://localhost:3001/api/accounts/focus"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    print("📡 Getting current focus...")
    response = requests.get(focus_url, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        focus_data = response.json()
        print(f"Current focus: {focus_data}")
        return focus_data
    else:
        print(f"❌ Failed to get focus: {response.text}")
        return None

def test_set_focus(token, focus):
    """Test setting user focus."""
    print(f"\n🎯 Setting focus to: {focus}")

    focus_url = "http://localhost:3001/api/accounts/focus"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(focus_url, json={"focus": focus}, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Focus set result: {result}")
        return result
    else:
        print(f"❌ Failed to set focus: {response.text}")
        return None

def main():
    """Main test function."""
    print("🚀 Testing Agent Interaction & Focus API")
    print("=" * 50)

    # Step 1: Login
    token = login_and_get_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return

    # Step 2: Test focus API
    current_focus = test_focus_api(token)

    if current_focus:
        # Step 3: Test setting focus to employer
        test_set_focus(token, "employer")

        # Step 4: Test setting focus back to candidate
        test_set_focus(token, "candidate")

    # Step 5: Test agent interaction
    test_agent_streaming(token)

    print("\n🎯 All tests completed!")

if __name__ == "__main__":
    main()
