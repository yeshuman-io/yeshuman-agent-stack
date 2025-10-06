#!/usr/bin/env python3
"""
Standalone memory test for Django checkpointer functionality.
Tests agent memory without Django test framework or external servers.
"""

import os
import sys
import asyncio
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yeshuman.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from agent.checkpointer import DjangoCheckpointSaver
from apps.threads.models import Thread
from django.contrib.auth import get_user_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.base import Checkpoint

User = get_user_model()

async def test_memory():
    """Test agent memory functionality."""
    print("🧠 Testing Agent Memory with Django Checkpointer")
    print("=" * 50)

    # Create test user
    user, created = await User.objects.aget_or_create(
        username='memory_test_user',
        defaults={
            'email': 'memory@test.com',
            'password': 'test123'
        }
    )
    print(f"👤 User: {user.username} (ID: {user.id})")

    # Test thread (use integer ID for Django compatibility)
    thread_id = 999001

    # Get checkpointer instance
    checkpointer = DjangoCheckpointSaver.get_instance()
    print("✅ Checkpointer instance obtained")

    # Simulate first conversation turn
    print("\n📝 Turn 1: 'My favorite color is blue'")
    config = {
        "configurable": {
            "thread_id": str(thread_id),  # LangGraph expects string
            "user_id": str(user.id),
            "user": user,
            "focus": "admin",
            "protocol": "graph"
        }
    }

    # Create checkpoint for first turn
    messages_1 = [
        HumanMessage(content="My favorite color is blue"),
        AIMessage(content="Blue is a wonderful color! It's associated with trust, loyalty, and calmness.")
    ]

    checkpoint_1 = Checkpoint(
        v=1,
        id="checkpoint_turn_1",
        ts="2024-01-01T10:00:00",
        channel_values={
            "messages": messages_1,
            "user_id": user.id,
            "tool_call_count": 0
        },
        channel_versions={"messages": 1, "user_id": 1, "tool_call_count": 1},
        versions_seen={},
        pending_sends=[]
    )

    # Save first checkpoint
    await checkpointer.aput(config, checkpoint_1, {"turn": 1})
    print("💾 First checkpoint saved")

    # Verify thread was created
    try:
        thread = await Thread.objects.aget(id=thread_id)
        print(f"🧵 Thread created: {thread.id} (User: {thread.user_id})")

        # Check checkpoint data
        if hasattr(thread, '_langgraph_checkpoint'):
            checkpoint_data = thread._langgraph_checkpoint
            print("📊 Checkpoint data saved to thread")
            saved_checkpoint = checkpoint_data['checkpoint']
            saved_messages = saved_checkpoint['channel_values']['messages']
            print(f"💬 Messages in checkpoint: {len(saved_messages)}")
        else:
            print("❌ No checkpoint data found on thread")

    except Thread.DoesNotExist:
        print("❌ Thread was not created")

    # Simulate second conversation turn
    print("\n📝 Turn 2: 'What is my favorite color?'")

    # Load previous state
    loaded_tuple = await checkpointer.aget_tuple(config)
    if loaded_tuple:
        print("✅ Previous state loaded from checkpointer")
        loaded_messages = loaded_tuple.checkpoint["channel_values"]["messages"]
        print(f"📚 Loaded {len(loaded_messages)} messages from history")

        # Add new message
        new_message = HumanMessage(content="What is my favorite color?")
        updated_messages = loaded_messages + [new_message]

        # Create AI response
        ai_response = AIMessage(content="Your favorite color is blue! You mentioned it in our previous conversation.")
        final_messages = updated_messages + [ai_response]

        # Save updated checkpoint
        checkpoint_2 = Checkpoint(
            v=2,
            id="checkpoint_turn_2",
            ts="2024-01-01T10:01:00",
            channel_values={
                "messages": final_messages,
                "user_id": user.id,
                "tool_call_count": 0
            },
            channel_versions={"messages": 2, "user_id": 1, "tool_call_count": 1},
            versions_seen={},
            pending_sends=[]
        )

        await checkpointer.aput(config, checkpoint_2, {"turn": 2})
        print("💾 Updated checkpoint saved")

        # Verify final state
        final_tuple = await checkpointer.aget_tuple(config)
        final_messages_count = len(final_tuple.checkpoint["channel_values"]["messages"])
        print(f"🎯 Final conversation has {final_messages_count} messages")

        # Check memory worked
        last_ai_message = final_tuple.checkpoint["channel_values"]["messages"][-1]
        if "blue" in last_ai_message.content.lower():
            print("🎉 SUCCESS: Agent remembered the favorite color!")
            print(f"🤖 AI Response: {last_ai_message.content}")
        else:
            print("❌ FAILED: Agent did not remember the favorite color")
            print(f"🤖 AI Response: {last_ai_message.content}")

    else:
        print("❌ FAILED: Could not load previous state")

    print("\n" + "=" * 50)
    print("🧠 Memory Test Complete")

if __name__ == "__main__":
    asyncio.run(test_memory())
