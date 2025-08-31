#!/usr/bin/env python
"""
Direct integration test for thread endpoints - no test database creation.
Run this script to test the thread system against the actual running server.
"""
import json
import requests
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yeshuman.settings')
import django
django.setup()

BASE_URL = 'http://127.0.0.1:8000'

def test_user_login():
    """Test user login and return JWT token."""
    print("🔐 Testing user login...")

    response = requests.post(f'{BASE_URL}/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    if response.status_code == 200:
        token = response.json()['token']
        print(f"✅ Login successful, token: {token[:20]}...")
        return token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_create_authenticated_thread(token):
    """Test creating a thread as authenticated user."""
    print("\n📝 Testing authenticated thread creation...")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(f'{BASE_URL}/api/threads',
                           json={'subject': 'Integration Test Thread'},
                           headers=headers)
    
    if response.status_code == 200:
        thread_data = response.json()
        print(f"✅ Thread created: {thread_data['id']}")
        print(f"   Subject: {thread_data['subject']}")
        print(f"   User ID: {thread_data['user_id']}")
        return thread_data['id']
    else:
        print(f"❌ Thread creation failed: {response.status_code} - {response.text}")
        return None

def test_create_anonymous_thread():
    """Test creating an anonymous thread."""
    print("\n👤 Testing anonymous thread creation...")
    
    response = requests.post(f'{BASE_URL}/api/threads',
                           json={
                               'subject': 'Anonymous Test Thread',
                               'session_id': 'test-session-123'
                           })
    
    if response.status_code == 200:
        thread_data = response.json()
        print(f"✅ Anonymous thread created: {thread_data['id']}")
        print(f"   Subject: {thread_data['subject']}")
        print(f"   User ID: {thread_data['user_id']}")
        return thread_data['id']
    else:
        print(f"❌ Anonymous thread creation failed: {response.status_code} - {response.text}")
        return None

def test_send_message_to_thread(thread_id, token):
    """Test sending a message to a thread."""
    print(f"\n💬 Testing message to thread {thread_id}...")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(f'{BASE_URL}/api/threads/{thread_id}/messages',
                           json={'message': 'Hello from integration test!'},
                           headers=headers)
    
    if response.status_code == 200:
        message_data = response.json()
        print(f"✅ Message sent successfully")
        print(f"   Response: {message_data}")
        return True
    else:
        print(f"❌ Message sending failed: {response.status_code} - {response.text}")
        return None

def test_get_thread_messages(thread_id, token):
    """Test getting messages from a thread."""
    print(f"\n📋 Testing get messages for thread {thread_id}...")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{BASE_URL}/api/threads/{thread_id}/messages',
                          headers=headers)
    
    if response.status_code == 200:
        messages = response.json()
        print(f"✅ Retrieved {len(messages)} messages")
        for msg in messages:
            print(f"   - {msg['message_type']}: {msg['text'][:50]}...")
        return messages
    else:
        print(f"❌ Get messages failed: {response.status_code} - {response.text}")
        return []

def test_stream_endpoint(thread_id, token):
    """Test the stream endpoint with thread context."""
    print(f"\n🌊 Testing stream endpoint with thread {thread_id}...")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(f'{BASE_URL}/agent/stream', 
                           json={
                               'message': 'What is 2+2?',
                               'thread_id': thread_id
                           },
                           headers=headers,
                           stream=True)
    
    if response.status_code == 200:
        print("✅ Stream endpoint accepted request")
        # Read a few chunks to verify it's working
        chunks_read = 0
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                print(f"   Chunk {chunks_read}: {chunk[:100]}...")
                chunks_read += 1
                if chunks_read >= 3:  # Limit for test
                    break
        response.close()
        return True
    else:
        print(f"❌ Stream endpoint failed: {response.status_code} - {response.text}")
        return False

def test_get_user_threads(token):
    """Test getting user's threads."""
    print("\n📚 Testing get user threads...")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{BASE_URL}/api/threads', headers=headers)
    
    if response.status_code == 200:
        threads = response.json()
        print(f"✅ Retrieved {len(threads)} user threads")
        for thread in threads[:3]:  # Show first 3
            print(f"   - {thread['id']}: {thread['subject']}")
        return threads
    else:
        print(f"❌ Get user threads failed: {response.status_code} - {response.text}")
        return []

def test_session_threads():
    """Test getting threads for a session."""
    print("\n🔗 Testing session threads...")

    # Note: Session threads endpoint doesn't exist yet, skipping this test
    print("⚠️  Session threads endpoint not implemented, skipping test")
    return []

def main():
    """Run all integration tests."""
    print("🚀 Starting Thread System Integration Tests")
    print("=" * 50)
    
    # Test login
    token = test_user_login()
    if not token:
        print("❌ Cannot proceed without login token")
        return
    
    # Test authenticated thread creation
    auth_thread_id = test_create_authenticated_thread(token)
    
    # Test anonymous thread creation  
    anon_thread_id = test_create_anonymous_thread()
    
    # Test sending messages
    if auth_thread_id:
        message_result = test_send_message_to_thread(auth_thread_id, token)
        if message_result:
            test_get_thread_messages(auth_thread_id, token)
            test_stream_endpoint(auth_thread_id, token)
    
    # Test getting user threads
    test_get_user_threads(token)
    
    # Test session threads
    test_session_threads()
    
    print("\n" + "=" * 50)
    print("🎉 Integration tests completed!")

if __name__ == '__main__':
    main()
