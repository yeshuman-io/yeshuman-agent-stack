"""
Tests for profiles app models.
"""

from django.test import TestCase
from apps.profiles.models import Profile


class ProfileModelTest(TestCase):
    """Test Profile model functionality."""

    def test_profile_creation(self):
        """Test that a profile can be created."""
        profile = Profile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.assertEqual(profile.first_name, "John")
        self.assertEqual(profile.last_name, "Doe")
        self.assertEqual(str(profile), "John Doe")
