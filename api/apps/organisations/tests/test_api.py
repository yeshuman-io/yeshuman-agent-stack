"""
Tests for organisations app API endpoints.
"""

from django.test import TestCase
from ninja.testing import TestClient
from apps.organisations.api import organisations_router
from apps.organisations.models import Organisation


class OrganisationsAPITest(TestCase):
    """Test organisations API endpoints."""

    def setUp(self):
        # Clear database state for test isolation
        Organisation.objects.all().delete()
        self.client = TestClient(organisations_router)

    def test_list_organisations_empty(self):
        """Test listing organisations when empty."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_organisation(self):
        """Test creating an organisation."""
        response = self.client.post("/", json={"name": "Test Org"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Org")
        self.assertIn("id", data)

    def test_get_organisation(self):
        """Test getting a specific organisation."""
        org = Organisation.objects.create(name="Test Org")
        response = self.client.get(f"/{org.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Org")
        self.assertEqual(data["id"], str(org.id))

    def test_list_organisations_with_data(self):
        """Test listing organisations when data exists."""
        # Create some organisations
        Organisation.objects.create(name="Company A")
        Organisation.objects.create(name="Company B")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(len(results), 2)

        # Check that results contain expected data
        names = [org["name"] for org in results]
        self.assertIn("Company A", names)
        self.assertIn("Company B", names)

    def test_create_organisation_simple(self):
        """Test creating an organisation with just a name."""
        data = {
            "name": "Simple Tech Corp"
        }

        response = self.client.post("/", json=data)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["name"], "Simple Tech Corp")
        self.assertIn("id", result)

    def test_get_organisation_not_found(self):
        """Test getting an organisation that doesn't exist."""
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f"/{fake_uuid}")
        self.assertEqual(response.status_code, 404)

    def test_create_organisation_invalid_data(self):
        """Test creating an organisation with invalid data."""
        # Missing required name field
        data = {
            "description": "Missing name field"
        }
        response = self.client.post("/", json=data)
        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_create_organisation_duplicate_name(self):
        """Test creating organisations with duplicate names."""
        # Create first organisation
        Organisation.objects.create(name="Duplicate Org")

        # Try to create another with same name
        # Note: The Organisation model doesn't have unique constraints on name
        # so this should succeed
        data = {
            "name": "Duplicate Org"
        }
        response = self.client.post("/", json=data)

        # This should succeed since there's no unique constraint
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["name"], "Duplicate Org")

        # Verify we now have 2 organisations with the same name
        orgs_with_name = Organisation.objects.filter(name="Duplicate Org")
        self.assertEqual(orgs_with_name.count(), 2)
