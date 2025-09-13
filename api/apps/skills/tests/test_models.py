"""
Tests for skills app models.
"""

from django.test import TestCase
from apps.skills.models import Skill


class SkillModelTest(TestCase):
    """Test Skill model functionality."""

    def test_skill_creation(self):
        """Test that a skill can be created."""
        # Clear existing skills first
        Skill.objects.all().delete()

        skill = Skill.objects.create(
            name="Python Programming"
        )
        self.assertEqual(skill.name, "Python Programming")
        self.assertEqual(str(skill), "Python Programming")
