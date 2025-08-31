"""
Tests for A2A (Agent-to-Agent) functionality.
"""
import json
from django.test import TestCase, Client
from django.utils import timezone
from a2a.models import Agent, A2AMessage, Task


class TestA2AAPI(TestCase):
    """Test A2A API endpoints."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = Client()
        
        # Clear any existing agents to ensure clean state
        Agent.objects.all().delete()
        
        # Create test agents
        self.agent1 = Agent.objects.create(
            name="test-agent-1",
            capabilities=["calculation", "text-processing"],
            status="online"
        )
        self.agent2 = Agent.objects.create(
            name="test-agent-2", 
            capabilities=["data-analysis", "reporting"],
            status="online"
        )
    
    def test_agent_registration(self):
        """Test agent registration endpoint."""
        payload = {
            "name": "new-agent",
            "endpoint_url": "http://localhost:9000",
            "capabilities": ["testing", "debugging"],
            "metadata": {"version": "1.0"}
        }
        
        response = self.client.post(
            '/a2a/agents/register',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_API_KEY='test-key-789'  # Use test key from .env
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('id', data)
        self.assertEqual(data['name'], 'new-agent')
        self.assertEqual(data['status'], 'online')
        self.assertEqual(data['capabilities'], ['testing', 'debugging'])
        
        # Verify agent was created in database
        agent = Agent.objects.get(name='new-agent')
        self.assertEqual(agent.endpoint_url, "http://localhost:9000")
        self.assertEqual(agent.metadata, {"version": "1.0"})
    
    def test_agent_discovery(self):
        """Test agent discovery endpoint."""
        response = self.client.get('/a2a/discover')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data), 2)
        agent_names = [agent['name'] for agent in data]
        self.assertIn('test-agent-1', agent_names)
        self.assertIn('test-agent-2', agent_names)
    
    def test_agent_discovery_with_capabilities(self):
        """Test agent discovery filtered by capabilities."""
        response = self.client.get('/a2a/discover?capabilities=calculation')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'test-agent-1')
        self.assertIn('calculation', data[0]['capabilities'])
    
    def test_send_message(self):
        """Test sending a message between agents."""
        payload = {
            "to_agent": "test-agent-2",
            "message_type": "task",
            "subject": "Test Task",
            "payload": {"action": "analyze", "data": [1, 2, 3]},
            "priority": 2,
            "response_required": True
        }
        
        response = self.client.post(
            '/a2a/messages/send',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_AGENT_NAME='test-agent-1'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('id', data)
        self.assertEqual(data['from_agent'], 'test-agent-1')
        self.assertEqual(data['to_agent'], 'test-agent-2')
        self.assertEqual(data['message_type'], 'task')
        self.assertEqual(data['status'], 'pending')
        
        # Verify message was created in database
        message = A2AMessage.objects.get(id=data['id'])
        self.assertEqual(message.subject, "Test Task")
        self.assertEqual(message.payload, {"action": "analyze", "data": [1, 2, 3]})
    
    def test_get_messages(self):
        """Test getting messages for an agent."""
        # Create a test message
        message = A2AMessage.objects.create(
            from_agent=self.agent1,
            to_agent=self.agent2,
            message_type="request",
            subject="Test Message",
            payload={"test": "data"},
            status="pending"
        )
        
        response = self.client.get('/a2a/messages/test-agent-2')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(message.id))
        self.assertEqual(data[0]['from_agent'], 'test-agent-1')
        self.assertEqual(data[0]['subject'], 'Test Message')
    
    def test_mark_message_read(self):
        """Test marking a message as read."""
        message = A2AMessage.objects.create(
            from_agent=self.agent1,
            to_agent=self.agent2,
            message_type="notification",
            payload={"info": "test"},
            status="delivered"
        )
        
        response = self.client.post(f'/a2a/messages/{message.id}/mark_read')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'read')
        
        # Verify message status was updated
        message.refresh_from_db()
        self.assertEqual(message.status, 'read')
        self.assertIsNotNone(message.read_at)
    
    def test_create_task(self):
        """Test creating a task."""
        payload = {
            "assigned_to": "test-agent-2",
            "title": "Data Analysis Task",
            "description": "Analyze the provided dataset",
            "task_type": "analysis",
            "parameters": {"dataset_id": "12345", "format": "csv"}
        }
        
        response = self.client.post(
            '/a2a/tasks/create',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_AGENT_NAME='test-agent-1',
            HTTP_X_API_KEY='test-key-789'  # Use test key from .env
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('id', data)
        self.assertEqual(data['created_by'], 'test-agent-1')
        self.assertEqual(data['assigned_to'], 'test-agent-2')
        self.assertEqual(data['title'], 'Data Analysis Task')
        self.assertEqual(data['status'], 'assigned')
        
        # Verify task was created in database
        task = Task.objects.get(id=data['id'])
        self.assertEqual(task.task_type, 'analysis')
        self.assertEqual(task.parameters, {"dataset_id": "12345", "format": "csv"})
    
    def test_get_agent_tasks(self):
        """Test getting tasks for an agent."""
        task = Task.objects.create(
            created_by=self.agent1,
            assigned_to=self.agent2,
            title="Test Task",
            description="Test description",
            status="assigned"
        )
        
        response = self.client.get('/a2a/tasks/test-agent-2')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(task.id))
        self.assertEqual(data[0]['title'], 'Test Task')
        self.assertEqual(data[0]['assigned_to'], 'test-agent-2')
    
    def test_agent_heartbeat(self):
        """Test agent heartbeat endpoint."""
        old_last_seen = self.agent1.last_seen
        
        response = self.client.post('/a2a/agents/test-agent-1/heartbeat')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('last_seen', data)
        
        # Verify timestamp was updated
        self.agent1.refresh_from_db()
        self.assertGreater(self.agent1.last_seen, old_last_seen)
    
    def test_agent_stream_endpoint(self):
        """Test SSE stream endpoint structure."""
        response = self.client.get('/a2a/stream/test-agent-1')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['Cache-Control'], 'no-cache')
        
        # Test that the stream contains connection confirmation
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('connected', content)
        self.assertIn('test-agent-1', content)


class TestA2AModels(TestCase):
    """Test A2A model functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing data to ensure clean state
        Agent.objects.all().delete()
        A2AMessage.objects.all().delete() 
        Task.objects.all().delete()
        
        self.agent1 = Agent.objects.create(
            name="model-test-agent-1",
            capabilities=["testing"],
            status="online"
        )
        self.agent2 = Agent.objects.create(
            name="model-test-agent-2", 
            capabilities=["verification"],
            status="online"
        )
    
    def test_agent_is_online(self):
        """Test Agent.is_online() method."""
        self.assertTrue(self.agent1.is_online())
        
        self.agent1.status = 'offline'
        self.assertFalse(self.agent1.is_online())
    
    def test_agent_update_heartbeat(self):
        """Test Agent.update_heartbeat() method."""
        old_last_seen = self.agent1.last_seen
        self.agent1.update_heartbeat()
        
        self.assertGreater(self.agent1.last_seen, old_last_seen)
    
    def test_message_mark_delivered(self):
        """Test A2AMessage.mark_delivered() method."""
        message = A2AMessage.objects.create(
            from_agent=self.agent1,
            to_agent=self.agent2,
            message_type="test",
            payload={"test": True},
            status="pending"
        )
        
        self.assertIsNone(message.delivered_at)
        message.mark_delivered()
        
        self.assertEqual(message.status, 'delivered')
        self.assertIsNotNone(message.delivered_at)
    
    def test_message_mark_read(self):
        """Test A2AMessage.mark_read() method."""
        message = A2AMessage.objects.create(
            from_agent=self.agent1,
            to_agent=self.agent2,
            message_type="test",
            payload={"test": True},
            status="delivered"
        )
        
        self.assertIsNone(message.read_at)
        message.mark_read()
        
        self.assertEqual(message.status, 'read')
        self.assertIsNotNone(message.read_at)
    
    def test_task_assign_to(self):
        """Test Task.assign_to() method."""
        task = Task.objects.create(
            created_by=self.agent1,
            title="Test Assignment",
            status="created"
        )
        
        self.assertIsNone(task.assigned_to)
        task.assign_to(self.agent2)
        
        self.assertEqual(task.assigned_to, self.agent2)
        self.assertEqual(task.status, 'assigned')
        self.assertIsNotNone(task.assigned_at)
    
    def test_task_complete(self):
        """Test Task.complete() method."""
        task = Task.objects.create(
            created_by=self.agent1,
            assigned_to=self.agent2,
            title="Test Completion",
            status="in_progress"
        )
        
        result_data = {"result": "success", "value": 42}
        task.complete(result_data)
        
        self.assertEqual(task.status, 'completed')
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.result, result_data)
        self.assertIsNotNone(task.completed_at)


class TestA2AAgentCards(TestCase):
    """Test A2A Agent Cards functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_agent_card_endpoint(self):
        """Test agent card endpoint returns Yes Human agent card."""
        response = self.client.get('/a2a/agent-card')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('agent_card', data)
        
        agent_card = data['agent_card']
        self.assertEqual(agent_card['name'], 'Yes Human Agent')
        self.assertIn('capabilities', agent_card)
        self.assertIn('endpoints', agent_card)
        self.assertIn('tags', agent_card)
        
        # Check that it has expected capabilities
        capability_names = [cap['name'] for cap in agent_card['capabilities']]
        self.assertIn('calculation', capability_names)
        self.assertIn('conversation', capability_names)
        self.assertIn('weather_lookup', capability_names)
        self.assertIn('text_analysis', capability_names)
    
    def test_agent_card_by_name(self):
        """Test getting agent card by name."""
        # Test Yes Human agent
        response = self.client.get('/a2a/agent-card/yeshuman')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('agent_card', data)
        self.assertEqual(data['agent_card']['name'], 'Yes Human Agent')
        
        # Test non-existent agent
        response = self.client.get('/a2a/agent-card/nonexistent')
        self.assertEqual(response.status_code, 404)
    
    def test_capability_matching(self):
        """Test capability matching endpoint."""
        import json
        
        # Test matching existing capabilities
        payload = {
            "required_capabilities": ["calculation", "conversation"],
            "required_tags": ["calculation", "conversation"]
        }
        response = self.client.post(
            '/a2a/capability-match',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['matches'])
        self.assertIn('agent_card', data)
        self.assertEqual(len(data['matching_capabilities']), 2)
        self.assertGreater(len(data['matching_tags']), 0)
        
        # Test non-matching capabilities
        payload = {
            "required_capabilities": ["nonexistent_capability"],
            "required_tags": []
        }
        response = self.client.post(
            '/a2a/capability-match',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data['matches'])
        self.assertIsNone(data['agent_card'])
        self.assertEqual(len(data['matching_capabilities']), 0)


class TestA2AAsyncTasks(TestCase):
    """Test A2A Async Tasks functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_list_task_types(self):
        """Test listing available task types."""
        response = self.client.get('/a2a/task-types')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('task_types', data)
        
        task_types = data['task_types']
        self.assertGreater(len(task_types), 0)
        
        # Check required fields
        for task_type in task_types:
            self.assertIn('type', task_type)
            self.assertIn('description', task_type)
            self.assertIn('example_params', task_type)
    
    def test_create_async_task(self):
        """Test creating an async task."""
        import json
        
        payload = {
            "task_type": "long_calculation",
            "params": {"expression": "2+2", "iterations": 5}
        }
        response = self.client.post(
            '/a2a/async-tasks',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('task_id', data)
        self.assertEqual(data['status'], 'created')
        self.assertIn('message', data)
        
        # Test task status endpoint
        task_id = data['task_id']
        status_response = self.client.get(f'/a2a/async-tasks/{task_id}')
        self.assertEqual(status_response.status_code, 200)
        
        status_data = status_response.json()
        self.assertEqual(status_data['task_id'], task_id)
        self.assertIn(status_data['status'], ['pending', 'running', 'completed'])
        self.assertGreaterEqual(status_data['progress'], 0.0)
        self.assertLessEqual(status_data['progress'], 100.0)
    
    def test_invalid_task_type(self):
        """Test creating task with invalid type."""
        import json
        
        payload = {
            "task_type": "nonexistent_task",
            "params": {}
        }
        response = self.client.post(
            '/a2a/async-tasks',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn('error', data)
    
    def test_nonexistent_task_status(self):
        """Test getting status of nonexistent task."""
        response = self.client.get('/a2a/async-tasks/nonexistent-task-id')
        self.assertEqual(response.status_code, 404)
        
        data = response.json()
        self.assertIn('error', data)
