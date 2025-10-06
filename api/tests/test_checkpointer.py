"""
Tests for Django Checkpointer functionality.

Tests multi-turn conversation persistence and state management.
"""
import os
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async

from agent.checkpointer import DjangoCheckpointSaver
from agent.graph import create_agent, astream_agent_tokens
from apps.threads.models import Thread
from apps.threads.services import get_thread_messages_as_langchain

User = get_user_model()


class CheckpointerTestCase(TestCase):
    """Test the Django checkpointer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.checkpointer = DjangoCheckpointSaver()

    def tearDown(self):
        """Clean up test data."""
        Thread.objects.all().delete()
        User.objects.all().delete()

    def test_checkpointer_creation(self):
        """Test that checkpointer can be instantiated."""
        assert self.checkpointer is not None
        assert hasattr(self.checkpointer, 'get_tuple')
        assert hasattr(self.checkpointer, 'put')

    def test_checkpointer_skips_anonymous_sessions(self):
        """Test that checkpointer skips persistence for anonymous/default sessions."""
        # Should return None for anonymous sessions
        config = {"configurable": {"thread_id": None}}
        result = self.checkpointer.get_tuple(config)
        assert result is None

        config = {"configurable": {"thread_id": "default"}}
        result = self.checkpointer.get_tuple(config)
        assert result is None

    def test_checkpointer_handles_missing_thread(self):
        """Test that checkpointer handles non-existent threads gracefully."""
        config = {"configurable": {"thread_id": "99999"}}  # Non-existent thread
        result = self.checkpointer.get_tuple(config)
        assert result is None  # Should not crash

    @pytest.mark.asyncio
    async def test_agent_creation_with_checkpointer(self):
        """Test that agent can be created with checkpointer."""
        with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}):
            agent = await create_agent(user=self.user)
            assert agent is not None
            # Check that the compiled graph has checkpointer
            assert hasattr(agent, 'checkpointer')

    def test_thread_creation_and_persistence(self):
        """Test that threads are created and can be persisted to."""
        # Create a thread
        thread = Thread.objects.create(
            user=self.user,
            subject="Test Thread"
        )

        # Test that checkpointer can load initial state from thread
        config = {"configurable": {"thread_id": str(thread.id)}}
        checkpoint = self.checkpointer.get_tuple(config)

        # Should create initial checkpoint from thread messages (empty initially)
        assert checkpoint is not None
        assert checkpoint.checkpoint is not None
        # For initial checkpoints created from threads, messages should be loaded from Django
        # The checkpointer creates a Checkpoint object with messages from get_thread_messages_as_langchain
        assert isinstance(checkpoint.checkpoint.channel_values.get("messages", []), list)

    def test_checkpointer_state_persistence(self):
        """Test that checkpointer can save and load state."""
        # Create a thread
        thread = Thread.objects.create(
            user=self.user,
            subject="Test Thread"
        )
        thread_id = str(thread.id)

        # Create a mock checkpoint
        from langgraph.checkpoint.base import Checkpoint, CheckpointTuple
        import datetime

        checkpoint = Checkpoint(
            v=1,
            id="test_checkpoint_123",
            ts=datetime.datetime.now().isoformat(),
            channel_values={
                "messages": [{"content": "test message", "type": "human"}],
                "user_id": str(self.user.id),
                "tools_done": True,
                "voice_messages": ["Test voice"],
                "last_voice_sig": "test_sig",
                "tool_call_count": 1
            },
            channel_versions={
                "messages": 1,
                "user_id": 1,
                "tools_done": 1,
                "voice_messages": 1,
                "last_voice_sig": 1,
                "tool_call_count": 1
            },
            versions_seen={},
            pending_sends=[]
        )

        config = {"configurable": {"thread_id": thread_id, "user_id": str(self.user.id)}}

        # Save checkpoint
        self.checkpointer.put(config, checkpoint, {"test": "metadata"})

        # Load checkpoint
        loaded = self.checkpointer.get_tuple(config)

        assert loaded is not None
        assert loaded.checkpoint.id == "test_checkpoint_123"
        assert loaded.checkpoint.channel_values["user_id"] == str(self.user.id)
        assert loaded.checkpoint.channel_values["voice_messages"] == ["Test voice"]
        assert loaded.checkpoint.channel_values["tool_call_count"] == 1

    @pytest.mark.asyncio
    async def test_checkpointer_thread_persistence(self):
        """Test that checkpointer persists state between simulated agent calls."""
        from langgraph.checkpoint.base import Checkpoint

        thread_id = "test_persistence_456"

        # Create a thread first
        thread = Thread.objects.create(
            id=thread_id,
            user=self.user,
            subject="Persistence Test"
        )

        # Simulate first agent checkpoint
        config = {"configurable": {"thread_id": thread_id, "user_id": str(self.user.id)}}
        checkpoint1 = Checkpoint(
            v=1,
            id="checkpoint_1",
            ts="2024-01-01T00:00:00",
            channel_values={
                "messages": [{"content": "Hello", "type": "human"}],
                "user_id": str(self.user.id),
                "voice_messages": ["Greeting processed"],
                "tool_call_count": 0
            },
            channel_versions={"messages": 1, "user_id": 1, "voice_messages": 1, "tool_call_count": 1},
            versions_seen={},
            pending_sends=[]
        )

        # Save first checkpoint
        await self.checkpointer.aput(config, checkpoint1, {"turn": 1})

        # Verify checkpoint was saved
        thread.refresh_from_db()
        assert hasattr(thread, '_langgraph_checkpoint')
        assert thread._langgraph_checkpoint is not None

        # Simulate second agent checkpoint (loading previous state)
        loaded = await self.checkpointer.aget_tuple(config)
        assert loaded is not None
        assert loaded.checkpoint.id == "checkpoint_1"
        assert len(loaded.checkpoint.channel_values["messages"]) == 1

        # Save updated checkpoint
        checkpoint2 = Checkpoint(
            v=2,
            id="checkpoint_2",
            ts="2024-01-01T00:00:01",
            channel_values={
                "messages": [
                    {"content": "Hello", "type": "human"},
                    {"content": "Hi there!", "type": "ai"}
                ],
                "user_id": str(self.user.id),
                "voice_messages": ["Greeting processed", "Response generated"],
                "tool_call_count": 0
            },
            channel_versions={"messages": 2, "user_id": 1, "voice_messages": 2, "tool_call_count": 1},
            versions_seen={},
            pending_sends=[]
        )

        await self.checkpointer.aput(config, checkpoint2, {"turn": 2})

        # Verify updated checkpoint
        loaded2 = await self.checkpointer.aget_tuple(config)
        assert loaded2.checkpoint.id == "checkpoint_2"
        assert len(loaded2.checkpoint.channel_values["messages"]) == 2
        assert len(loaded2.checkpoint.channel_values["voice_messages"]) == 2

        print("✅ Thread persistence test completed")

    @pytest.mark.asyncio
    async def test_checkpointer_state_isolation(self):
        """Test that different threads maintain isolated state."""
        from langgraph.checkpoint.base import Checkpoint

        thread_id_1 = "isolation_test_1"
        thread_id_2 = "isolation_test_2"

        # Create threads
        thread1 = Thread.objects.create(id=thread_id_1, user=self.user, subject="Thread 1")
        thread2 = Thread.objects.create(id=thread_id_2, user=self.user, subject="Thread 2")

        # Save different checkpoints to each thread
        config1 = {"configurable": {"thread_id": thread_id_1, "user_id": str(self.user.id)}}
        config2 = {"configurable": {"thread_id": thread_id_2, "user_id": str(self.user.id)}}

        checkpoint1 = Checkpoint(
            v=1, id="thread1_checkpoint", ts="2024-01-01T00:00:00",
            channel_values={"messages": [{"content": "Red", "type": "human"}], "user_id": str(self.user.id), "voice_messages": ["Red processed"], "tool_call_count": 0},
            channel_versions={"messages": 1, "user_id": 1, "voice_messages": 1, "tool_call_count": 1},
            versions_seen={}, pending_sends=[]
        )

        checkpoint2 = Checkpoint(
            v=1, id="thread2_checkpoint", ts="2024-01-01T00:00:00",
            channel_values={"messages": [{"content": "Blue", "type": "human"}], "user_id": str(self.user.id), "voice_messages": ["Blue processed"], "tool_call_count": 0},
            channel_versions={"messages": 1, "user_id": 1, "voice_messages": 1, "tool_call_count": 1},
            versions_seen={}, pending_sends=[]
        )

        await self.checkpointer.aput(config1, checkpoint1, {"thread": "1"})
        await self.checkpointer.aput(config2, checkpoint2, {"thread": "2"})

        # Verify each thread has its own checkpoint
        loaded1 = await self.checkpointer.aget_tuple(config1)
        loaded2 = await self.checkpointer.aget_tuple(config2)

        assert loaded1.checkpoint.id == "thread1_checkpoint"
        assert loaded2.checkpoint.id == "thread2_checkpoint"
        assert loaded1.checkpoint.channel_values["messages"][0]["content"] == "Red"
        assert loaded2.checkpoint.channel_values["messages"][0]["content"] == "Blue"

        print("✅ State isolation test completed")

    def test_checkpointer_skips_invalid_threads(self):
        """Test checkpointer handles invalid thread_ids gracefully."""
        # Test with non-existent thread
        config = {"configurable": {"thread_id": "nonexistent_999999"}}
        result = self.checkpointer.get_tuple(config)
        assert result is None  # Should not crash

        # Test with string that looks like int but doesn't exist
        config = {"configurable": {"thread_id": "123456789"}}
        result = self.checkpointer.get_tuple(config)
        assert result is None  # Should not crash

        print("✅ Invalid thread handling test completed")

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_checkpointer_memory_simulation(self):
        """Test checkpointer memory by simulating agent state saves/loads."""
        # Create a test user
        user = User.objects.create_user(
            username='memory_test_user',
            email='memory@example.com',
            password='testpass123'
        )

        thread_id = "memory_simulation_test_001"

        # Simulate first agent interaction
        print("📝 Simulating first agent interaction...")

        # Create initial state with first message
        from langchain_core.messages import HumanMessage, AIMessage
        from langgraph.checkpoint.base import Checkpoint

        initial_messages = [HumanMessage(content="My favorite color is blue")]
        initial_state = {
            "messages": initial_messages,
            "user_id": user.id,
            "tool_call_count": 0
        }

        # Simulate agent response
        ai_response = AIMessage(content="Blue is a great color!")
        updated_messages = initial_messages + [ai_response]
        updated_state = {
            "messages": updated_messages,
            "user_id": user.id,
            "tool_call_count": 0
        }

        # Save state via checkpointer
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": str(user.id),
                "user": user,
                "focus": "admin",
                "protocol": "graph"
            }
        }

        checkpoint = Checkpoint(
            v=1,
            id="checkpoint_1",
            ts="2024-01-01T00:00:00",
            channel_values=updated_state,
            channel_versions={"messages": 1, "user_id": 1, "tool_call_count": 1},
            versions_seen={},
            pending_sends=[]
        )

        # This should create the thread and save checkpoint
        import asyncio
        asyncio.run(self.checkpointer.aput(config, checkpoint, {"turn": 1}))

        # Verify thread was created and state saved
        thread = Thread.objects.get(id=thread_id)
        self.assertIsNotNone(thread)
        self.assertEqual(thread.user_id, user.id)
        self.assertIsNotNone(thread._langgraph_checkpoint)

        print("✅ First interaction state saved")

        # Simulate loading state for second interaction
        print("📝 Simulating second agent interaction (loading state)...")

        loaded_tuple = asyncio.run(self.checkpointer.aget_tuple(config))
        self.assertIsNotNone(loaded_tuple)

        loaded_state = loaded_tuple.checkpoint.channel_values
        loaded_messages = loaded_state["messages"]

        # Should have the conversation history
        self.assertEqual(len(loaded_messages), 2)
        self.assertEqual(loaded_messages[0].content, "My favorite color is blue")
        self.assertEqual(loaded_messages[1].content, "Blue is a great color!")

        print("✅ Previous conversation state loaded successfully")

        # Simulate second message and state update
        new_human_message = HumanMessage(content="What is my favorite color?")
        final_messages = loaded_messages + [new_human_message]

        final_checkpoint = Checkpoint(
            v=2,
            id="checkpoint_2",
            ts="2024-01-01T00:01:00",
            channel_values={
                "messages": final_messages,
                "user_id": user.id,
                "tool_call_count": 0
            },
            channel_versions={"messages": 2, "user_id": 1, "tool_call_count": 1},
            versions_seen={},
            pending_sends=[]
        )

        # Save updated state
        asyncio.run(self.checkpointer.aput(config, final_checkpoint, {"turn": 2}))

        # Verify final state
        final_tuple = asyncio.run(self.checkpointer.aget_tuple(config))
        final_loaded_messages = final_tuple.checkpoint.channel_values["messages"]

        self.assertEqual(len(final_loaded_messages), 3)
        self.assertEqual(final_loaded_messages[2].content, "What is my favorite color?")

        print("✅ Agent memory test completed - checkpointer maintains conversation history!")
        print("✅ Agent can resume conversations with full context!")
