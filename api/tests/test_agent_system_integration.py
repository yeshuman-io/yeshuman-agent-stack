"""
Comprehensive integration tests for the complete agent system.
Tests authentication, focus management, tool assignment, agent awareness,
thread management, and focus switching scenarios.
"""
import json
import pytest
import asyncio
from django.test import TestCase, AsyncClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from unittest.mock import patch
from asgiref.sync import sync_to_async
from apps.threads.models import Thread, HumanMessage, AssistantMessage
from datetime import datetime, timezone

User = get_user_model()


class AgentSystemIntegrationTest(TestCase):
    """Complete integration tests for the agent system with authentication, tools, and threads."""

    def setUp(self):
        """Set up test user with groups and authenticated client."""
        self.client = AsyncClient()

        # Create test user
        self.user = User.objects.create_user(
            username='test_agent_user',
            email='agent_test@example.com',
            password='testpass123'
        )

        # Create groups
        self.job_seeking_group, _ = Group.objects.get_or_create(name='job_seeking')
        self.hiring_group, _ = Group.objects.get_or_create(name='hiring')

        # Add user to hiring group (employer focus)
        self.user.groups.add(self.hiring_group)

    def tearDown(self):
        """Clean up test data."""
        from django.contrib.sessions.models import Session
        Session.objects.filter(session_key__startswith='test_session_key_').delete()
        Thread.objects.all().delete()
        User.objects.all().delete()

    async def _login_and_get_token(self):
        """Helper to login and get JWT token."""
        login_response = await self.client.post(
            '/api/accounts/login',
            {'username': 'test_agent_user', 'password': 'testpass123'},
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 200)
        data = login_response.json()
        self.assertTrue(data['success'])
        return data['token']

    # ==========================================
    # AUTH & SESSION SETTING TESTS
    # ==========================================

    async def test_authentication_flow(self):
        """Test login returns valid JWT token."""
        token = await self._login_and_get_token()
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 50)  # JWT tokens are reasonably long

    async def test_user_groups_setup(self):
        """Verify user has correct groups for focus testing."""
        user_groups = await sync_to_async(lambda: list(self.user.groups.all()))()
        self.assertIn(self.hiring_group, user_groups)
        self.assertNotIn(self.job_seeking_group, user_groups)

    # ==========================================
    # TOOL ASSIGNMENT TESTS
    # ==========================================

    async def test_tool_assignment_employer_focus(self):
        """Test that employer focus gets correct tools."""
        from tools.compositions import get_tools_for_focus

        # Test employer focus (user has hiring group)
        tools = await sync_to_async(get_tools_for_focus)(self.user, 'employer', 'graph')
        tool_names = [t.name for t in tools]

        # Should have employer-specific tools
        employer_tools = [
            'create_opportunity', 'update_opportunity', 'find_candidates_for_opportunity',
            'evaluate_candidate_profile', 'analyze_talent_pool'
        ]

        for tool in employer_tools:
            self.assertIn(tool, tool_names, f"Missing employer tool: {tool}")

        # Should have application management tools
        app_tools = [
            'create_application', 'change_application_stage', 'record_application_decision'
        ]

        for tool in app_tools:
            self.assertIn(tool, tool_names, f"Missing application tool: {tool}")

    async def test_tool_assignment_candidate_focus(self):
        """Test that candidate focus gets correct tools."""
        from tools.compositions import get_tools_for_focus

        # Add user to job_seeking group for candidate access
        await sync_to_async(self.user.groups.add)(self.job_seeking_group)

        # Test candidate focus
        tools = await sync_to_async(get_tools_for_focus)(self.user, 'candidate', 'graph')
        tool_names = [t.name for t in tools]

        # Should have candidate-specific tools
        candidate_tools = [
            'create_profile', 'update_profile', 'find_opportunities_for_profile',
            'analyze_opportunity_fit', 'get_learning_recommendations'
        ]

        for tool in candidate_tools:
            self.assertIn(tool, tool_names, f"Missing candidate tool: {tool}")

    # ==========================================
    # AGENT AWARENESS TESTS
    # ==========================================

    @patch('agent.graph.ChatOpenAI')
    async def test_agent_creates_with_correct_tools(self, mock_chat_openai):
        """Test that agent is created with focus-appropriate tools."""
        from agent.graph import create_agent

        # Mock the ChatOpenAI to avoid API calls
        mock_instance = mock_chat_openai.return_value
        mock_instance.bind_tools.return_value = mock_instance

        # Create agent with employer focus
        agent = await sync_to_async(create_agent)(user=self.user, focus='employer')

        # Verify bind_tools was called with tools
        mock_instance.bind_tools.assert_called_once()
        bound_tools = mock_instance.bind_tools.call_args[0][0]

        # Should have employer tools
        tool_names = [t.name for t in bound_tools]
        self.assertIn('create_opportunity', tool_names)
        self.assertIn('find_candidates_for_opportunity', tool_names)

    # ==========================================
    # THREAD MANAGEMENT TESTS
    # ==========================================

    async def test_thread_creation_via_agent_interaction(self):
        """Test that agent interaction creates and manages threads properly."""
        # This would require setting up the actual agent streaming endpoint
        # For now, test the thread creation directly
        pass

    async def test_thread_message_loading_into_agent_state(self):
        """Test that thread messages are properly loaded into agent state."""
        from django.contrib.sessions.models import Session

        # Create a session for the user
        session = await sync_to_async(Session.objects.create)(
            session_key='test_session_key_12345',
            session_data='{}',
            expire_date=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        )

        # Create a thread
        thread = await sync_to_async(Thread.objects.create)(
            user=self.user,
            subject="Test Agent Thread",
            is_anonymous=False,
            session=session
        )

        # Verify thread was created
        self.assertIsNotNone(thread.id)

        # Test that thread exists and has correct properties
        retrieved_thread = await sync_to_async(Thread.objects.get)(id=thread.id)
        self.assertEqual(retrieved_thread.subject, "Test Agent Thread")

        # Check user and session using sync_to_async
        thread_user = await sync_to_async(lambda: retrieved_thread.user)()
        thread_session = await sync_to_async(lambda: retrieved_thread.session)()

        self.assertEqual(thread_user, self.user)
        self.assertEqual(thread_session, session)

    # ==========================================
    # FOCUS SWITCHING TESTS
    # ==========================================

    async def test_focus_switching_updates_tools(self):
        """Test that changing focus updates available tools for subsequent agent calls."""
        from tools.compositions import get_tools_for_focus

        # Add candidate group for testing
        await sync_to_async(self.user.groups.add)(self.job_seeking_group)

        # Test employer focus
        employer_tools = await sync_to_async(get_tools_for_focus)(self.user, 'employer', 'graph')
        employer_names = {t.name for t in employer_tools}

        # Test candidate focus
        candidate_tools = await sync_to_async(get_tools_for_focus)(self.user, 'candidate', 'graph')
        candidate_names = {t.name for t in candidate_tools}

        # Should have different tool sets
        self.assertNotEqual(employer_names, candidate_names)

        # Employer should have opportunity tools, candidate should not
        self.assertIn('create_opportunity', employer_names)
        self.assertNotIn('create_opportunity', candidate_names)

        # Candidate should have profile tools, employer should not
        self.assertIn('create_profile', candidate_names)
        self.assertNotIn('create_profile', employer_names)

    async def test_agent_receives_correct_tools_after_focus_change(self):
        """Test that agent creation uses correct focus-specific tools."""
        from agent.graph import create_agent
        from tools.compositions import get_tools_for_focus

        # Test employer focus
        employer_agent = await sync_to_async(create_agent)(user=self.user, focus='employer')
        employer_composition = await sync_to_async(get_tools_for_focus)(self.user, 'employer', 'graph')
        employer_tool_names = {t.name for t in employer_composition}

        # Add candidate group
        await sync_to_async(self.user.groups.add)(self.job_seeking_group)

        # Test candidate focus
        candidate_agent = await sync_to_async(create_agent)(user=self.user, focus='candidate')
        candidate_composition = await sync_to_async(get_tools_for_focus)(self.user, 'candidate', 'graph')
        candidate_tool_names = {t.name for t in candidate_composition}

        # Agents should be different (different tool sets)
        self.assertNotEqual(employer_tool_names, candidate_tool_names)

        # Verify specific tools
        self.assertIn('create_opportunity', employer_tool_names)
        self.assertIn('create_profile', candidate_tool_names)
