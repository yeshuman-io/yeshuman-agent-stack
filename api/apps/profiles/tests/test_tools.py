"""
Tests for profiles app tools.
"""

from django.test import TestCase
from apps.profiles.tools import CreateProfileTool, UpdateProfileTool, ListProfilesTool


class TestProfilesTools(TestCase):
    """Light tests for profiles tools functionality."""

    def test_create_profile_tool(self):
        """Test create profile tool basic functionality."""
        # Test the tool (using sync version for Django test compatibility)
        tool = CreateProfileTool()
        result = tool._run(
            first_name="Test",
            last_name="User",
            email="test.user@example.com",
            skills=["Python", "Django"],
            experiences=[{
                "title": "Software Engineer",
                "company": "Test Company",
                "description": "Great work experience",
                "start_date": "2020-01-01",
                "end_date": "2023-01-01"
            }]
        )

        # Basic assertions
        self.assertIn("✅ Candidate profile created successfully", result)
        self.assertIn("Test User", result)
        self.assertIn("test.user@example.com", result)

    def test_update_profile_tool(self):
        """Test update profile tool basic functionality."""
        from apps.profiles.factories import ProfileFactory

        # Create test data
        profile = ProfileFactory()

        # Test the tool (sync version for simplicity)
        tool = UpdateProfileTool()
        result = tool._run(
            profile_id=str(profile.id),
            first_name="Updated",
            last_name="Name",
            email="updated@example.com"
        )

        # Basic assertions
        self.assertIn("✅ Profile updated successfully", result)
        self.assertIn("Updated Name", result)

    def test_list_profiles_tool(self):
        """Test list profiles tool basic functionality."""
        from apps.profiles.factories import ProfileFactory

        # Create test data
        profile = ProfileFactory()

        # Test the tool
        tool = ListProfilesTool()
        result = tool._run(limit=10)

        # Basic assertions
        self.assertGreater(len(result), 0)  # Should return some results
