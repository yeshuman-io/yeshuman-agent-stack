"""
Integration tests for the thread system - testing real API functionality.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from unittest.mock import patch
from threads.models import Thread, HumanMessage, AssistantMessage

User = get_user_model()


class ThreadIntegrationTests(TestCase):
    """Integration tests for thread system without mocking database operations."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        # Create test user directly (no async needed)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_thread_creation_via_api(self):
        """Test creating threads through the API."""
        # Login first to get JWT token
        login_response = self.client.post('/api/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()['token']
        
        # Create thread via API
        thread_response = self.client.post(
            '/api/threads/',
            json.dumps({'subject': 'Test Thread'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(thread_response.status_code, 201)
        thread_data = thread_response.json()
        
        # Verify thread was created
        self.assertIn('id', thread_data)
        self.assertEqual(thread_data['subject'], 'Test Thread')
        self.assertFalse(thread_data['is_anonymous'])
    
    def test_anonymous_thread_creation(self):
        """Test creating anonymous threads."""
        # Create thread without authentication
        thread_response = self.client.post(
            '/api/threads/',
            json.dumps({'subject': 'Anonymous Thread'}),
            content_type='application/json'
        )
        
        self.assertEqual(thread_response.status_code, 201)
        thread_data = thread_response.json()
        
        # Verify anonymous thread
        self.assertTrue(thread_data['is_anonymous'])
        self.assertIsNotNone(thread_data.get('session_id'))
    
    @patch('agent.graph.astream_agent_tokens')
    def test_stream_endpoint_with_thread_context(self, mock_astream):
        """Test the stream endpoint with thread context."""
        # Mock the agent streaming response
        async def mock_stream():
            yield {'type': 'token', 'content': 'Hello'}
            yield {'type': 'token', 'content': ' there!'}
            yield {'type': 'end'}
        
        mock_astream.return_value = mock_stream()
        
        # Login to get token
        login_response = self.client.post('/api/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        token = login_response.json()['token']
        
        # Create a thread first
        thread_response = self.client.post(
            '/api/threads/',
            json.dumps({'subject': 'Stream Test'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        thread_id = thread_response.json()['id']
        
        # Send message to stream endpoint
        stream_response = self.client.post(
            '/agent/stream',
            json.dumps({
                'message': 'Hello agent!',
                'thread_id': thread_id
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        # Should accept the request
        self.assertEqual(stream_response.status_code, 200)
        
        # Verify thread has messages
        thread = Thread.objects.get(id=thread_id)
        messages = list(thread.message_set.all().order_by('created_at'))
        
        # Should have human message and assistant message
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertIsInstance(messages[1], AssistantMessage)
        self.assertEqual(messages[0].text, 'Hello agent!')
    
    def test_anonymous_session_persistence(self):
        """Test that anonymous sessions persist threads correctly."""
        session_id = 'test-session-123'
        
        # Create anonymous thread
        thread_response = self.client.post(
            '/api/threads/',
            json.dumps({
                'subject': 'Session Thread',
                'session_id': session_id
            }),
            content_type='application/json'
        )
        
        thread_id = thread_response.json()['id']
        
        # Get threads for session
        session_threads_response = self.client.get(
            f'/api/threads/session/{session_id}/'
        )
        
        self.assertEqual(session_threads_response.status_code, 200)
        threads = session_threads_response.json()
        
        # Should find our thread
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]['id'], thread_id)
    
    def test_thread_migration_on_login(self):
        """Test migrating anonymous thread to user on login."""
        session_id = 'migration-session-456'
        
        # Create anonymous thread
        thread_response = self.client.post(
            '/api/threads/',
            json.dumps({
                'subject': 'Migration Thread',
                'session_id': session_id
            }),
            content_type='application/json'
        )
        
        thread_id = thread_response.json()['id']
        
        # Login to get token
        login_response = self.client.post('/api/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        token = login_response.json()['token']
        
        # Migrate thread to user
        migrate_response = self.client.post(
            f'/api/threads/{thread_id}/migrate/',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(migrate_response.status_code, 200)
        
        # Verify thread is now owned by user
        thread = Thread.objects.get(id=thread_id)
        self.assertEqual(thread.user_id, str(self.user.id))
        self.assertFalse(thread.is_anonymous)
        self.assertIsNone(thread.session_id)
    
    def test_user_thread_access_control(self):
        """Test that users can only access their own threads."""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Login as first user and create thread
        login_response = self.client.post('/api/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        token1 = login_response.json()['token']
        
        thread_response = self.client.post(
            '/api/threads/',
            json.dumps({'subject': 'Private Thread'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token1}'
        )
        thread_id = thread_response.json()['id']
        
        # Login as second user
        login_response2 = self.client.post('/api/login/', {
            'username': 'otheruser',
            'password': 'otherpass123'
        }, content_type='application/json')
        token2 = login_response2.json()['token']
        
        # Try to access first user's thread
        access_response = self.client.get(
            f'/api/threads/{thread_id}/',
            HTTP_AUTHORIZATION=f'Bearer {token2}'
        )
        
        # Should be forbidden
        self.assertEqual(access_response.status_code, 404)

