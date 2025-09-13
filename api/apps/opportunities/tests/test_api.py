"""
Tests for opportunities app API endpoints.
"""

from django.test import TestCase
from ninja.testing import TestClient
from apps.opportunities.api import opportunities_router
from apps.opportunities.models import Opportunity
from apps.organisations.models import Organisation


class OpportunitiesAPITest(TestCase):
    """Test opportunities API endpoints."""

    def setUp(self):
        self.client = TestClient(opportunities_router)

    def test_list_opportunities_empty(self):
        """Test listing opportunities when empty."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_opportunity(self):
        """Test creating an opportunity."""
        org = Organisation.objects.create(name="Test Org")
        response = self.client.post("/", json={
            "title": "Software Engineer",
            "description": "Great job",
            "organisation_id": str(org.id)
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Software Engineer")
        self.assertEqual(data["organisation_name"], "Test Org")
        self.assertIn("id", data)

    def test_get_opportunity(self):
        """Test getting a specific opportunity."""
        org = Organisation.objects.create(name="Test Org")
        opp = Opportunity.objects.create(
            title="Software Engineer",
            description="Great job",
            organisation=org
        )
        response = self.client.get(f"/{opp.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Software Engineer")
        self.assertEqual(data["organisation_name"], "Test Org")
