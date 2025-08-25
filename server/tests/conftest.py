import os
import django
from django.conf import settings

# Setup Django settings before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bookedai.settings")
django.setup()

import pytest
import pytest_asyncio
from django.test import Client
from asgiref.sync import sync_to_async

from chats.models import Chat, HumanMessage, BookedAIMessage
from agent.agent import BookedAI

@pytest.fixture
def api_client():
    """Return a Django test client."""
    return Client()

@pytest.fixture
def chat():
    """Return a Chat instance."""
    return Chat.objects.create(subject="Test Chat")

@pytest_asyncio.fixture
async def async_chat():
    """Return a Chat instance for async contexts."""
    create_chat = sync_to_async(Chat.objects.create)
    return await create_chat(subject="Test Chat")

@pytest.fixture
def chat_without_subject():
    """Return a Chat instance without a subject."""
    return Chat.objects.create()

@pytest_asyncio.fixture
async def async_chat_without_subject():
    """Return a Chat instance without a subject for async contexts."""
    create_chat = sync_to_async(Chat.objects.create)
    return await create_chat()

@pytest.fixture
def human_message(chat):
    """Return a HumanMessage instance."""
    return HumanMessage.objects.create(chat=chat, text="Test human message")

@pytest_asyncio.fixture
async def async_human_message():
    """Return a HumanMessage instance for async contexts."""
    # Create a chat first
    create_chat = sync_to_async(Chat.objects.create)
    chat = await create_chat(subject="Test Chat")
    
    # Create the message
    create_message = sync_to_async(HumanMessage.objects.create)
    return await create_message(chat=chat, text="Test human message")

@pytest.fixture
def bookedai_message(chat):
    """Return a BookedAIMessage instance."""
    return BookedAIMessage.objects.create(chat=chat, text="Test BookedAI response")

@pytest_asyncio.fixture
async def async_bookedai_message(async_chat):
    """Return a BookedAIMessage instance for async contexts."""
    create_message = sync_to_async(BookedAIMessage.objects.create)
    return await create_message(chat=async_chat, text="Test BookedAI response")

@pytest.fixture
def bookedai_agent():
    """Return a BookedAI agent instance."""
    return BookedAI()

@pytest.fixture
def chat_with_messages():
    """Return a Chat instance with multiple messages."""
    chat = Chat.objects.create(subject="Chat with messages")
    HumanMessage.objects.create(chat=chat, text="Human message 1")
    BookedAIMessage.objects.create(chat=chat, text="BookedAI message 1")
    HumanMessage.objects.create(chat=chat, text="Human message 2")
    BookedAIMessage.objects.create(chat=chat, text="BookedAI message 2")
    return chat

@pytest_asyncio.fixture
async def async_chat_with_messages():
    """Return a Chat instance with multiple messages for async contexts."""
    create_chat = sync_to_async(Chat.objects.create)
    chat = await create_chat(subject="Chat with messages")
    
    create_human_msg = sync_to_async(HumanMessage.objects.create)
    create_bookedai_msg = sync_to_async(BookedAIMessage.objects.create)
    
    await create_human_msg(chat=chat, text="Human message 1")
    await create_bookedai_msg(chat=chat, text="BookedAI message 1")
    await create_human_msg(chat=chat, text="Human message 2")
    await create_bookedai_msg(chat=chat, text="BookedAI message 2")
    
    return chat 