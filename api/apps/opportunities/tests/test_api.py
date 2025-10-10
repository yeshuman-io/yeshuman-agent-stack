"""
Tests for opportunities app API endpoints.
"""

from django.test import TestCase
from ninja.testing import TestClient
from apps.opportunities.api import opportunities_router
from apps.opportunities.models import Opportunity
from apps.organisations.models import Organisation
import numpy as np


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

    def test_list_opportunities_with_search_filters_pagination(self):
        """Test the enhanced list opportunities endpoint with search, filters, and pagination."""
        # Create test organisations
        org1 = Organisation.objects.create(name="TechCorp")
        org2 = Organisation.objects.create(name="DataSys")

        # Create test opportunities
        opp1 = Opportunity.objects.create(
            title="Senior Python Developer",
            description="Looking for experienced Python developer with Django skills",
            organisation=org1
        )
        opp2 = Opportunity.objects.create(
            title="Data Scientist",
            description="Machine learning and data analysis role",
            organisation=org2
        )
        opp3 = Opportunity.objects.create(
            title="Frontend Developer",
            description="React and TypeScript development position",
            organisation=org1
        )

        # Test basic listing
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["results"]), 3)
        self.assertTrue(data["has_next"])

        # Test keyword search
        response = self.client.get("/?q=Python&mode=keyword")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["title"], "Senior Python Developer")

        # Test organisation filter
        response = self.client.get("/?organisation=TechCorp")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertTrue(all(opp["organisation_name"] == "TechCorp" for opp in data["results"]))

        # Test pagination
        response = self.client.get("/?page=1&page_size=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 2)
        self.assertTrue(data["has_next"])

        response = self.client.get("/?page=2&page_size=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["page"], 2)
        self.assertFalse(data["has_next"])

        # Test combined filters
        response = self.client.get("/?q=developer&organisation=TechCorp&page_size=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        titles = [opp["title"] for opp in data["results"]]
        self.assertIn("Senior Python Developer", titles)
        self.assertIn("Frontend Developer", titles)

    def test_list_opportunities_semantic_search_fallback(self):
        """Test semantic search mode and fallback behavior."""
        # Create test data
        org = Organisation.objects.create(name="TestOrg")
        opp = Opportunity.objects.create(
            title="Software Engineer",
            description="Looking for developers",
            organisation=org
        )

        # Test semantic mode without embeddings (should fallback to keyword)
        response = self.client.get("/?q=developer&mode=semantic")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)

        # Test hybrid mode without embeddings (should fallback to keyword)
        response = self.client.get("/?q=software&mode=hybrid")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)

        # Test invalid mode (should fallback to keyword)
        response = self.client.get("/?q=software&mode=invalid")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)

    def test_list_opportunities_with_embeddings(self):
        """Test semantic and hybrid search with embeddings."""
        # Create test data with mock embeddings
        org = Organisation.objects.create(name="TestOrg")
        opp1 = Opportunity.objects.create(
            title="Python Developer",
            description="Django web development",
            organisation=org,
            embedding=np.random.rand(1536).astype(np.float32)
        )
        opp2 = Opportunity.objects.create(
            title="Data Analyst",
            description="SQL and Excel skills",
            organisation=org,
            embedding=np.random.rand(1536).astype(np.float32)
        )

        # Test semantic mode with embeddings
        response = self.client.get("/?q=python&mode=semantic")
        self.assertEqual(response.status_code, 200)
        # Note: Actual semantic matching depends on embedding similarity
        # This test ensures the endpoint doesn't crash

        # Test hybrid mode with embeddings
        response = self.client.get("/?q=django&mode=hybrid")
        self.assertEqual(response.status_code, 200)
        # Similar to semantic, ensures no crashes