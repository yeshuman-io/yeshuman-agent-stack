"""
Comprehensive tests for the thread-based conversation system.

Tests cover:
- Thread creation and management
- Anonymous vs authenticated user flows
- Message persistence and context continuity
- Stream endpoint integration
- Thread migration on user login
"""

import pytest
import json
from django.test import TestCase, AsyncClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, AsyncMock
from asgiref.sync import sync_to_async

from apps.threads.models import Thread, HumanMessage, AssistantMessage
from apps.threads.services import (
    get_or_create_thread,
    get_user_threads,
    get_session_threads,
    migrate_anonymous_thread_to_user,
    create_human_message,
    create_assistant_message,
    get_thread_messages_as_langchain
)

User = get_user_model()


class ThreadSystemTestCase(TestCase):
    """Base test case with common setup for thread system tests."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = AsyncClient()

    def tearDown(self):
        """Clean up test data."""
        Thread.objects.all().delete()
        User.objects.all().delete()


class ThreadModelTests(ThreadSystemTestCase):
    """Test Thread model functionality."""

    def test_thread_creation_authenticated_user(self):
        """Test creating a thread for an authenticated user."""
        thread = Thread.objects.create(
            user_id=str(self.user.id),
            subject="Test Thread",
            is_anonymous=False
        )

        self.assertEqual(thread.user_id, str(self.user.id))
        self.assertEqual(thread.subject, "Test Thread")
        self.assertFalse(thread.is_anonymous)
        self.assertIsNone(thread.session_id)

    def test_thread_creation_anonymous_user(self):
        """Test creating a thread for an anonymous user."""
        thread = Thread.objects.create(
            session_id="session_123",
            subject="Anonymous Thread",
            is_anonymous=True
        )

        self.assertIsNone(thread.user_id)
        self.assertEqual(thread.session_id, "session_123")
        self.assertTrue(thread.is_anonymous)


class ThreadServiceTests(ThreadSystemTestCase):
    """Test thread service functions."""

    async def test_get_or_create_thread_authenticated(self):
        """Test get_or_create_thread for authenticated user."""
        # Create new thread
        thread = await get_or_create_thread(
            user_id=str(self.user.id),
            subject="New Thread"
        )

        self.assertEqual(thread.user_id, str(self.user.id))
        self.assertEqual(thread.subject, "New Thread")
        self.assertFalse(thread.is_anonymous)

        # Get existing thread
        existing_thread = await get_or_create_thread(
            user_id=str(self.user.id),
            thread_id=str(thread.id)
        )

        self.assertEqual(thread.id, existing_thread.id)

    async def test_get_or_create_thread_anonymous(self):
        """Test get_or_create_thread for anonymous user."""
        # Create new anonymous thread
        thread = await get_or_create_thread(
            session_id="session_123",
            subject="Anonymous Thread"
        )

        self.assertIsNone(thread.user_id)
        self.assertEqual(thread.session_id, "session_123")
        self.assertTrue(thread.is_anonymous)

    async def test_get_user_threads(self):
        """Test getting threads for a user."""
        # Create multiple threads for user
        await get_or_create_thread(str(self.user.id), "Thread 1")
        await get_or_create_thread(str(self.user.id), "Thread 2")

        threads = await get_user_threads(str(self.user.id))
        self.assertEqual(len(threads), 2)

    async def test_get_session_threads(self):
        """Test getting threads for a session."""
        # Create multiple threads for session
        await get_or_create_thread(session_id="session_123", subject="Thread 1")
        await get_or_create_thread(session_id="session_123", subject="Thread 2")

        threads = await get_session_threads("session_123")
        self.assertEqual(len(threads), 2)

    async def test_migrate_anonymous_thread_to_user(self):
        """Test migrating anonymous thread to authenticated user."""
        # Create anonymous thread
        thread = await get_or_create_thread(
            session_id="session_123",
            subject="Anonymous Thread"
        )

        # Migrate to user
        success = await migrate_anonymous_thread_to_user(str(thread.id), str(self.user.id))

        self.assertTrue(success)

        # Refresh thread from database
        await sync_to_async(thread.refresh_from_db)()
        self.assertEqual(thread.user_id, str(self.user.id))
        self.assertFalse(thread.is_anonymous)
        self.assertIsNone(thread.session_id)

    async def test_message_creation_and_context(self):
        """Test creating messages and maintaining conversation context."""
        # Create thread
        thread = await get_or_create_thread(str(self.user.id), "Test Thread")

        # Add human message
        human_msg = await create_human_message(str(thread.id), "Hello, how are you?")
        self.assertEqual(human_msg.text, "Hello, how are you?")
        self.assertEqual(human_msg.thread.id, thread.id)

        # Add AI response
        ai_msg = await create_assistant_message(str(thread.id), "I'm doing well, thank you!")
        self.assertEqual(ai_msg.text, "I'm doing well, thank you!")
        self.assertEqual(ai_msg.thread.id, thread.id)

        # Test context retrieval
        messages = await get_thread_messages_as_langchain(str(thread.id))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, "Hello, how are you?")
        self.assertEqual(messages[1].content, "I'm doing well, thank you!")


class ThreadAPITests(ThreadSystemTestCase):
    """Test thread API endpoints."""

    async def test_create_thread_authenticated(self):
        """Test creating a thread as authenticated user."""
        # Login user
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        login_response = await self.client.post(
            reverse('auth:login'),
            data=json.dumps(login_data),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, 200)

        token = login_response.json()['token']

        # Create thread
        thread_data = {
            "subject": "Test Thread",
            "message": "Hello world"
        }
        response = await self.client.post(
            reverse('api-1:create_thread'),
            data=json.dumps(thread_data),
            content_type='application/json',
            headers={'Authorization': f'Bearer {token}'}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['subject'], "Test Thread")
        self.assertEqual(data['user_id'], str(self.user.id))
        self.assertEqual(data['message_count'], 1)

    async def test_thread_access_control(self):
        """Test that users can only access their own threads."""
        # Create thread for user
        thread = await get_or_create_thread(str(self.user.id), "Private Thread")

        # Create another user
        other_user = await sync_to_async(User.objects.create_user)(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )

        # Login as other user
        login_data = {
            "username": "otheruser",
            "password": "otherpass123"
        }
        login_response = await self.client.post(
            reverse('auth:login'),
            data=json.dumps(login_data),
            content_type='application/json'
        )
        token = login_response.json()['token']

        # Try to access first user's thread
        response = await self.client.get(
            reverse('api-1:get_thread_detail', kwargs={'thread_id': str(thread.id)}),
            headers={'Authorization': f'Bearer {token}'}
        )

        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)


class StreamEndpointTests(ThreadSystemTestCase):
    """Test stream endpoint with thread integration."""

    @patch('agent.graph.astream_agent_tokens')
    async def test_stream_with_session_persistence(self, mock_astream):
        """Test streaming with session-based persistence."""
        # Mock the streaming generator
        async def mock_generator():
            yield {"type": "message", "content": "Hello"}
            yield {"type": "message", "content": " there!"}
            yield {"type": "done", "content": ""}

        mock_astream.return_value = mock_generator()

        # Send message with session ID
        stream_data = {
            "message": "Hello, how are you?",
            "session_id": "test_session_123"
        }

        response = await self.client.post(
            reverse('agent:stream'),
            data=json.dumps(stream_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        # Check that thread was created for session
        threads = await get_session_threads("test_session_123")
        self.assertEqual(len(threads), 1)
        self.assertTrue(threads[0].is_anonymous)
        self.assertEqual(threads[0].session_id, "test_session_123")

    @patch('agent.graph.astream_agent_tokens')
    async def test_stream_with_existing_thread(self, mock_astream):
        """Test streaming with existing thread context."""
        # Create thread with existing message
        thread = await get_or_create_thread(str(self.user.id), "Existing Thread")
        await create_human_message(str(thread.id), "Previous message")

        # Mock streaming
        async def mock_generator():
            yield {"type": "message", "content": "I see"}
            yield {"type": "message", "content": " your previous message!"}
            yield {"type": "done", "content": ""}

        mock_astream.return_value = mock_generator()

        # Login user
        login_data = {"username": "testuser", "password": "testpass123"}
        login_response = await self.client.post(
            reverse('auth:login'),
            data=json.dumps(login_data),
            content_type='application/json'
        )
        token = login_response.json()['token']

        # Send message to existing thread
        stream_data = {
            "message": "Continue our conversation",
            "thread_id": str(thread.id)
        }

        response = await self.client.post(
            reverse('agent:stream'),
            data=json.dumps(stream_data),
            content_type='application/json',
            headers={'Authorization': f'Bearer {token}'}
        )

        self.assertEqual(response.status_code, 200)

        # Verify the streaming function was called with thread context
        mock_astream.assert_called_once()
        call_args = mock_astream.call_args
        # Should have been called with the thread messages
        self.assertIsNotNone(call_args[1].get('messages'))


class MigrationTests(ThreadSystemTestCase):
    """Test thread migration functionality."""

    async def test_anonymous_to_authenticated_migration(self):
        """Test migrating anonymous thread to authenticated user."""
        # Create anonymous thread
        thread = await get_or_create_thread(
            session_id="session_123",
            subject="Anonymous Conversation"
        )
        await create_human_message(str(thread.id), "Hello as anonymous user")

        # Verify it's anonymous
        self.assertTrue(thread.is_anonymous)
        self.assertIsNone(thread.user_id)
        self.assertEqual(thread.session_id, "session_123")

        # Migrate to authenticated user
        success = await migrate_anonymous_thread_to_user(str(thread.id), str(self.user.id))

        self.assertTrue(success)

        # Refresh and verify migration
        thread.refresh_from_db()
        self.assertFalse(thread.is_anonymous)
        self.assertEqual(thread.user_id, str(self.user.id))
        self.assertIsNone(thread.session_id)

        # Verify messages are preserved
        messages = await get_thread_messages_as_langchain(str(thread.id))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Hello as anonymous user")

    async def test_migration_nonexistent_thread(self):
        """Test migration of non-existent thread."""
        success = await migrate_anonymous_thread_to_user("nonexistent-id", str(self.user.id))
        self.assertFalse(success)

    async def test_migration_already_owned_thread(self):
        """Test migration of thread that already belongs to a user."""
        # Create user-owned thread
        thread = await get_or_create_thread(str(self.user.id), "User Thread")

        # Try to migrate it (should fail)
        success = await migrate_anonymous_thread_to_user(str(thread.id), str(self.user.id))
        self.assertFalse(success)


class IntegrationTests(ThreadSystemTestCase):
    """Integration tests for complete conversation flows."""

    async def test_complete_anonymous_conversation_flow(self):
        """Test complete flow: anonymous -> login -> continue conversation."""
        # Phase 1: Anonymous conversation
        session_id = "integration_test_session"

        # First message as anonymous
        stream_data = {
            "message": "Hello, I'm interested in Python programming",
            "session_id": session_id
        }

        with patch('agent.graph.astream_agent_tokens') as mock_stream:
            async def mock_gen():
                yield {"type": "message", "content": "Great! Python is excellent"}
                yield {"type": "done", "content": ""}

            mock_stream.return_value = mock_gen()

            response = await self.client.post(
                reverse('agent:stream'),
                data=json.dumps(stream_data),
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 200)

        # Verify anonymous thread created
        threads = await get_session_threads(session_id)
        self.assertEqual(len(threads), 1)
        thread = threads[0]
        self.assertTrue(thread.is_anonymous)

        # Phase 2: User logs in
        login_data = {"username": "testuser", "password": "testpass123"}
        login_response = await self.client.post(
            reverse('auth:login'),
            data=json.dumps(login_data),
            content_type='application/json'
        )
        token = login_response.json()['token']

        # Phase 3: Migrate anonymous thread to user
        success = await migrate_anonymous_thread_to_user(str(thread.id), str(self.user.id))
        self.assertTrue(success)

        # Phase 4: Continue conversation as authenticated user
        continue_data = {
            "message": "Can you show me a simple Python example?",
            "thread_id": str(thread.id)
        }

        with patch('agent.graph.astream_agent_tokens') as mock_stream:
            async def mock_gen2():
                yield {"type": "message", "content": "Here's a simple example:"}
                yield {"type": "message", "content": " print('Hello, World!')"}
                yield {"type": "done", "content": ""}

            mock_stream.return_value = mock_gen2()

            response = await self.client.post(
                reverse('agent:stream'),
                data=json.dumps(continue_data),
                content_type='application/json',
                headers={'Authorization': f'Bearer {token}'}
            )

            self.assertEqual(response.status_code, 200)

        # Verify thread now belongs to user and has all messages
        thread.refresh_from_db()
        self.assertEqual(thread.user_id, str(self.user.id))
        self.assertFalse(thread.is_anonymous)

        # Check conversation context
        messages = await get_thread_messages_as_langchain(str(thread.id))
        self.assertEqual(len(messages), 3)  # 2 human + 1 AI from first message

    async def test_multiple_sessions_isolation(self):
        """Test that different sessions don't interfere with each other."""
        # Create conversation in session 1
        session1_data = {
            "message": "Session 1 message",
            "session_id": "session_1"
        }

        with patch('agent.graph.astream_agent_tokens'):
            await self.client.post(
                reverse('agent:stream'),
                data=json.dumps(session1_data),
                content_type='application/json'
            )

        # Create conversation in session 2
        session2_data = {
            "message": "Session 2 message",
            "session_id": "session_2"
        }

        with patch('agent.graph.astream_agent_tokens'):
            await self.client.post(
                reverse('agent:stream'),
                data=json.dumps(session2_data),
                content_type='application/json'
            )

        # Verify isolation
        session1_threads = await get_session_threads("session_1")
        session2_threads = await get_session_threads("session_2")

        self.assertEqual(len(session1_threads), 1)
        self.assertEqual(len(session2_threads), 1)
        self.assertNotEqual(session1_threads[0].id, session2_threads[0].id)


if __name__ == '__main__':
    pytest.main([__file__])

