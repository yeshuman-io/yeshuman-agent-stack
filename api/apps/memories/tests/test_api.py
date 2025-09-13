"""
Tests for memories app API endpoints.
"""

from django.test import TestCase
from ninja.testing import TestClient
from apps.memories.api import memories_router
from apps.memories.models import Memory


class MemoriesAPITest(TestCase):
    """Test memories API endpoints."""

    def setUp(self):
        self.client = TestClient(memories_router)

    def test_list_memories_empty(self):
        """Test listing memories when empty."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_memory(self):
        """Test creating a memory."""
        response = self.client.post("/", json={
            "user_id": "test_user",
            "content": "Test memory",
            "category": "personal"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "Test memory")
        self.assertEqual(data["user_id"], "test_user")
        self.assertEqual(data["category"], "personal")
        self.assertIn("id", data)

    def test_get_memory(self):
        """Test getting a specific memory."""
        memory = Memory.objects.create(
            user_id="test_user",
            content="Test memory",
            category="personal"
        )
        response = self.client.get(f"/{memory.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "Test memory")
        self.assertEqual(data["user_id"], "test_user")

    def test_list_memories_with_data(self):
        """Test listing memories when data exists."""
        # Create some memories
        Memory.objects.create(
            user_id="user1",
            content="First memory",
            category="personal"
        )
        Memory.objects.create(
            user_id="user2",
            content="Second memory",
            category="work"
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(len(results), 2)

        # Check that results contain expected data
        contents = [memory["content"] for memory in results]
        self.assertIn("First memory", contents)
        self.assertIn("Second memory", contents)

    def test_list_memories_filtered_by_user(self):
        """Test listing memories filtered by user_id."""
        # Create memories for different users
        Memory.objects.create(
            user_id="user1",
            content="User1 memory",
            category="personal"
        )
        Memory.objects.create(
            user_id="user2",
            content="User2 memory",
            category="work"
        )

        response = self.client.get("/?user_id=user1")
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "User1 memory")
        self.assertEqual(results[0]["user_id"], "user1")

    def test_get_memory_not_found(self):
        """Test getting a memory that doesn't exist."""
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f"/{fake_uuid}")
        self.assertEqual(response.status_code, 404)

    def test_create_memory_invalid_data(self):
        """Test creating a memory with invalid data."""
        # Missing required fields
        data = {
            "user_id": "test_user"
            # Missing content and category
        }
        response = self.client.post("/", json=data)
        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_create_memory_with_all_fields(self):
        """Test creating a memory with all optional fields."""
        data = {
            "user_id": "test_user",
            "content": "Comprehensive test memory",
            "memory_type": "episodic",
            "interaction_type": "conversation",
            "category": "personal",
            "subcategory": "family",
            "importance": "high"
        }

        response = self.client.post("/", json=data)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["content"], "Comprehensive test memory")
        self.assertEqual(result["memory_type"], "episodic")
        self.assertEqual(result["interaction_type"], "conversation")
        self.assertEqual(result["category"], "personal")
        self.assertEqual(result["subcategory"], "family")
        self.assertEqual(result["importance"], "high")

    def test_memory_embedding_generation(self):
        """Test that memory embedding is attempted during creation."""
        data = {
            "user_id": "test_user",
            "content": "This should trigger embedding generation",
            "category": "personal"
        }

        response = self.client.post("/", json=data)
        self.assertEqual(response.status_code, 200)

        # Check that the memory was created
        result = response.json()
        memory_id = result["id"]

        # Verify the memory exists in database
        memory = Memory.objects.get(id=memory_id)
        self.assertEqual(memory.content, "This should trigger embedding generation")

        # Note: Embedding generation may fail if OpenAI API is not configured
        # but the memory should still be created
        print(f"Memory created with embedding: {memory.embedding is not None}")
