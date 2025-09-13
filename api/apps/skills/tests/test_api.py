"""
Tests for skills app API endpoints.
"""

from django.test import TestCase
from ninja.testing import TestClient
from apps.skills.api import skills_router
from apps.skills.models import Skill


class SkillsAPITest(TestCase):
    """Test skills API endpoints."""

    def setUp(self):
        # Clear database state for test isolation
        Skill.objects.all().delete()
        self.client = TestClient(skills_router)

    def test_list_skills_empty(self):
        """Test listing skills when empty."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_skill(self):
        """Test creating a skill."""
        response = self.client.post("/", json={"name": "Python"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Python")
        self.assertIn("id", data)

    def test_get_skill(self):
        """Test getting a specific skill."""
        skill = Skill.objects.create(name="Python")
        response = self.client.get(f"/{skill.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Python")
        self.assertEqual(data["id"], str(skill.id))

    def test_list_skills_with_data(self):
        """Test listing skills when data exists."""
        # Create some skills
        Skill.objects.create(name="Python")
        Skill.objects.create(name="JavaScript")
        Skill.objects.create(name="TypeScript")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(len(results), 3)

        # Check that results contain expected data
        names = [skill["name"] for skill in results]
        self.assertIn("Python", names)
        self.assertIn("JavaScript", names)
        self.assertIn("TypeScript", names)

    def test_create_skill_duplicate_name(self):
        """Test creating a skill with duplicate name."""
        # Create first skill
        Skill.objects.create(name="Python")

        # Try to create another with same name
        response = self.client.post("/", json={"name": "Python"})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("already exists", data["error"])

    def test_get_skill_not_found(self):
        """Test getting a skill that doesn't exist."""
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f"/{fake_uuid}")

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "Skill not found")

    def test_create_skill_case_sensitive(self):
        """Test that skill names are case-sensitive."""
        # Create first skill
        Skill.objects.create(name="python")

        # Try to create another with different case
        response = self.client.post("/", json={"name": "Python"})

        # Should succeed since names are case-sensitive
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Python")

    def test_create_skill_empty_name(self):
        """Test creating a skill with empty name."""
        response = self.client.post("/", json={"name": ""})

        # Should fail validation
        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_create_skill_whitespace_name(self):
        """Test creating a skill with whitespace-only name."""
        response = self.client.post("/", json={"name": "   "})

        # Should succeed as Pydantic doesn't validate whitespace by default
        self.assertEqual(response.status_code, 200)
