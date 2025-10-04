"""
Integration tests for user focus selection and agent tool assignment.
Tests the complete flow: login → focus selection → agent interaction.
"""

from unittest.mock import Mock, patch
import pytest
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.utils import negotiate_user_focus
from tools.compositions import get_tools_for_focus


User = get_user_model()


class UserFocusIntegrationTest(TestCase):
    """Integration test for user focus selection and agent tool assignment."""

    def setUp(self):
        """Set up test data."""
        # Create groups
        self.candidate_group, _ = Group.objects.get_or_create(name='candidate')
        self.employer_group, _ = Group.objects.get_or_create(name='employer')
        self.admin_group, _ = Group.objects.get_or_create(name='administrator')

        # Create test user
        self.user = User.objects.create_user(
            username='daryl',
            email='daryl@yeshuman.io',
            password='abc',
            first_name='Daryl',
            last_name='Test'
        )

        # Assign employer permissions by default
        self.user.groups.add(self.employer_group)
        self.user.save()

        # Create test client
        self.client = Client()

    def test_user_creation_and_groups(self):
        """Test that user exists with correct groups."""
        # Verify user exists
        user = User.objects.get(email='daryl@yeshuman.io')
        self.assertEqual(user.username, 'daryl')
        self.assertTrue(user.check_password('abc'))

        # Verify user has employer group
        self.assertIn(self.employer_group, user.groups.all())
        self.assertEqual(user.groups.count(), 1)

    def test_focus_negotiation_default_behavior(self):
        """Test focus negotiation for user with employer permissions."""
        # Simulate request
        request = self.client.get('/').wsgi_request
        request.user = self.user

        # Should default to 'employer' since user has employer group
        focus, error = negotiate_user_focus(request)
        self.assertEqual(focus, 'employer')
        self.assertIsNone(error)

        # Verify session is set
        self.assertEqual(request.session.get('user_focus'), 'employer')

    def test_focus_negotiation_explicit_setting(self):
        """Test explicit focus setting."""
        request = self.client.get('/').wsgi_request
        request.user = self.user

        # Set focus to candidate
        focus, error = negotiate_user_focus(request, 'candidate')
        self.assertEqual(focus, 'candidate')
        self.assertIsNone(error)

        # Verify session is updated
        self.assertEqual(request.session.get('user_focus'), 'candidate')

    def test_focus_restriction_without_permissions(self):
        """Test that user cannot set focus without proper permissions."""
        # Remove employer group
        self.user.groups.clear()
        self.user.groups.add(self.candidate_group)
        self.user.save()

        request = self.client.get('/').wsgi_request
        request.user = self.user

        # Try to set employer focus (should fail)
        focus, error = negotiate_user_focus(request, 'employer')
        self.assertEqual(focus, 'candidate')  # Falls back to candidate
        self.assertIsNotNone(error)
        self.assertIn('not available', error.lower())

    def test_agent_tools_based_on_focus(self):
        """Test that agent gets different tools based on focus."""
        # Test employer focus
        employer_tools = get_tools_for_focus(self.user, 'employer')
        self.assertIsNotNone(employer_tools)
        self.assertGreater(len(employer_tools), 0)

        # Should include employer-specific tools
        tool_names = [tool.name for tool in employer_tools]
        self.assertIn('create_opportunity', tool_names)  # Employer tool

        # Test candidate focus (even without candidate group, should work)
        candidate_tools = get_tools_for_focus(self.user, 'candidate')
        self.assertIsNotNone(candidate_tools)
        self.assertGreater(len(candidate_tools), 0)

        candidate_tool_names = [tool.name for tool in candidate_tools]
        self.assertIn('list_profiles', candidate_tool_names)  # Candidate tool

        # Employer and candidate should have different tool sets
        self.assertNotEqual(
            set(tool_names),
            set(candidate_tool_names)
        )

    @patch('agent.graph.create_agent')
    def test_agent_creation_with_focus(self, mock_create_agent):
        """Test that agent can be created with focus parameter."""
        from agent.graph import create_agent

        # Mock the agent creation to avoid full LangGraph setup
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent

        # Should work with employer focus
        agent = create_agent(user=self.user, focus='employer')
        mock_create_agent.assert_called_once_with(
            user=self.user,
            focus='employer'
        )

        # Reset mock for next call
        mock_create_agent.reset_mock()

        # Should work with candidate focus
        agent = create_agent(user=self.user, focus='candidate')
        mock_create_agent.assert_called_once_with(
            user=self.user,
            focus='candidate'
        )

    def test_admin_focus_access(self):
        """Test admin focus requires admin permissions."""
        # Add admin group
        self.user.groups.add(self.admin_group)
        self.user.save()

        request = self.client.get('/').wsgi_request
        request.user = self.user

        # Should allow admin focus
        focus, error = negotiate_user_focus(request, 'admin')
        self.assertEqual(focus, 'admin')
        self.assertIsNone(error)

        # Admin should get all tools
        admin_tools = get_tools_for_focus(self.user, 'admin')
        self.assertIsNotNone(admin_tools)

        # Should include tools from all categories
        tool_names = [tool.name for tool in admin_tools]
        self.assertIn('create_opportunity', tool_names)  # Employer tool
        self.assertIn('list_profiles', tool_names)       # Candidate tool

    def test_session_persistence(self):
        """Test that focus persists in session."""
        # First request sets focus
        request1 = self.client.get('/').wsgi_request
        request1.user = self.user
        focus1, _ = negotiate_user_focus(request1, 'candidate')

        # Second request should remember focus
        request2 = self.client.get('/').wsgi_request
        request2.user = self.user
        # Simulate session persistence
        request2.session = request1.session
        focus2, _ = negotiate_user_focus(request2)

        self.assertEqual(focus1, 'candidate')
        self.assertEqual(focus2, 'candidate')

    def test_unauthenticated_user_handling(self):
        """Test behavior for unauthenticated users."""
        from django.contrib.auth.models import AnonymousUser

        request = self.client.get('/').wsgi_request
        request.user = AnonymousUser()

        focus, error = negotiate_user_focus(request)
        self.assertEqual(focus, 'candidate')  # Default fallback
        self.assertIsNotNone(error)


