"""
Tests for organisations app models.
"""

from django.test import TestCase
from apps.organisations.models import Organisation


class OrganisationModelTest(TestCase):
    """Test Organisation model functionality."""

    def test_organisation_creation(self):
        """Test that an organisation can be created."""
        # Clear existing organisations first
        Organisation.objects.all().delete()

        org = Organisation.objects.create(
            name="Test Organisation"
        )
        self.assertEqual(org.name, "Test Organisation")
        self.assertEqual(str(org), "Test Organisation")
