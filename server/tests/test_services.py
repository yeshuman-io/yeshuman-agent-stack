import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from asgiref.sync import sync_to_async
import asyncio
import logging
import uuid

from chats.models import Chat, HumanMessage, BookedAIMessage
from chats.services import (
    get_or_create_chat,
    get_all_chat_messages,
    create_human_message,
    create_bookedai_message
)

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db

@pytest.mark.asyncio
class TestChatServices:
    """Tests for the chat services module"""
    
    async def test_get_or_create_chat_new(self):
        """Test that get_or_create_chat creates a new chat if it doesn't exist"""
        # First create a chat with a known subject to get its ID
        unique_subject = f"Test Chat {uuid.uuid4()}"
        chat_obj = await sync_to_async(Chat.objects.create)(subject=unique_subject)
        chat_id = str(chat_obj.id)
        
        # Delete the chat to simulate it not existing
        await sync_to_async(chat_obj.delete)()
        
        # Verify the chat doesn't exist
        chat_count = await sync_to_async(lambda: Chat.objects.filter(id=chat_id).count())()
        assert chat_count == 0
        
        # Call the service function with the chat ID
        chat = await get_or_create_chat(chat_id)
        
        # Verify the chat was created with the correct ID
        assert str(chat.id) == chat_id
        
        # Verify the chat exists in the database
        chat_count_after = await sync_to_async(lambda: Chat.objects.filter(id=chat_id).count())()
        assert chat_count_after == 1
    
    async def test_get_or_create_chat_existing(self, async_chat):
        """Test that get_or_create_chat returns an existing chat if it exists"""
        # Call the function
        retrieved_chat = await get_or_create_chat(async_chat.id)
        
        # Verify the chat was returned
        assert retrieved_chat.id == async_chat.id
        chat_count = await sync_to_async(lambda: Chat.objects.filter(id=async_chat.id).count())()
        assert chat_count == 1
    
    async def test_get_all_chat_messages(self, async_chat_with_messages):
        """Test that get_all_chat_messages returns all messages for a chat"""
        # Call the function
        messages, exists = await get_all_chat_messages(async_chat_with_messages.id)
        
        # Verify the messages were returned
        assert len(messages) == 4
        assert exists == True
        
        # Verify the messages contain the expected data
        # Note: The order might be different since we're returning a list of dicts
        texts = [msg['text'] for msg in messages]
        assert "BookedAI message 2" in texts
        assert "Human message 2" in texts
        assert "BookedAI message 1" in texts
        assert "Human message 1" in texts
    
    async def test_get_all_chat_messages_nonexistent_chat(self):
        """Test that get_all_chat_messages returns empty list for nonexistent chat"""
        # Use a numeric ID that doesn't exist
        chat_id = 99999
        
        # Call the function
        messages, exists = await get_all_chat_messages(chat_id)
        
        # Verify an empty list was returned
        assert len(messages) == 0
        assert exists == False
        
        # Verify the chat was NOT created (the function doesn't create chats)
        chat_count = await sync_to_async(lambda: Chat.objects.filter(id=chat_id).count())()
        assert chat_count == 0
    
    async def test_create_human_message(self, async_chat):
        """Test that create_human_message creates a human message"""
        # Call the function
        message = await create_human_message(async_chat.id, "Hello, BookedAI!")
        
        # Verify the message was created
        assert isinstance(message, HumanMessage)
        assert message.text == "Hello, BookedAI!"
        assert message.chat.id == async_chat.id
        
        # Verify the message is in the database
        message_count = await sync_to_async(lambda: HumanMessage.objects.filter(chat=async_chat).count())()
        assert message_count == 1
        message_text = await sync_to_async(lambda: HumanMessage.objects.filter(chat=async_chat).first().text)()
        assert message_text == "Hello, BookedAI!"
    
    async def test_create_bookedai_message(self, async_chat):
        """Test that create_bookedai_message creates a BookedAI message"""
        # Call the function
        message = await create_bookedai_message(async_chat.id, "I can help with that!")
        
        # Verify the message was created
        assert isinstance(message, BookedAIMessage)
        assert message.text == "I can help with that!"
        assert message.chat.id == async_chat.id
        
        # Verify the message is in the database
        message_count = await sync_to_async(lambda: BookedAIMessage.objects.filter(chat=async_chat).count())()
        assert message_count == 1
        message_text = await sync_to_async(lambda: BookedAIMessage.objects.filter(chat=async_chat).first().text)()
        assert message_text == "I can help with that!"

@pytest.mark.asyncio
class TestAgentServices:
    """Tests for the agent services module"""
    
    @pytest_asyncio.fixture
    async def async_chat(self):
        """Create a chat instance for async tests"""
        create_chat = sync_to_async(Chat.objects.create)
        chat = await create_chat(subject="Test Chat")
        return chat
    
    @pytest_asyncio.fixture
    async def async_human_message(self, async_chat):
        """Create a human message for async tests"""
        create_message = sync_to_async(HumanMessage.objects.create)
        message = await create_message(
            chat=async_chat,
            text="Test human message"
        )
        return message

# Helper function to add timeout to async generators
async def async_timeout(agen, timeout):
    """Add a timeout to an async generator."""
    try:
        async with asyncio.timeout(timeout):
            async for item in agen:
                yield item
    except asyncio.TimeoutError:
        # Clean up if needed
        logger.error(f"Async generator timed out after {timeout} seconds")
        raise 