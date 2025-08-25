from django.db.models import QuerySet as DjangoQuerySet
from django.forms.models import model_to_dict
from asgiref.sync import sync_to_async
from typing import Optional, Tuple

from .models import Chat, Message, HumanMessage, BookedAIMessage


async def get_chat(chat_id: str) -> Optional[Chat]:
    """
    Get a chat with the given ID.

    Args:
        chat_id: The ID of the chat to get

    Returns:
        The chat object, or None if the chat does not exist
    """
    try:
        return await sync_to_async(Chat.objects.get)(id=chat_id)
    except Chat.DoesNotExist:
        return None


async def get_or_create_chat(chat_id: Optional[str] = None) -> Chat:
    """
    Get or create a chat with the given ID.
    
    If chat_id is None or empty, a new chat will be created.
    If chat_id is provided and exists, the existing chat will be returned.
    If chat_id is provided but doesn't exist, a new chat with that ID will be created.

    Args:
        chat_id: The ID of the chat to get or create, or None to create a new chat

    Returns:
        The chat object
    """
    if not chat_id:
        # Create a new chat without specifying an ID
        chat_obj = await sync_to_async(Chat.objects.create)()
        return chat_obj
    
    try:
        # Try to get the existing chat
        chat_obj = await sync_to_async(Chat.objects.get)(id=chat_id)
        return chat_obj
    except Chat.DoesNotExist:
        # Create a new chat with the specified ID
        chat_obj = await sync_to_async(Chat.objects.create)(id=chat_id)
        return chat_obj


async def get_all_chat_messages(chat_id: str) -> list:
    """
    Get all messages for a given chat ID.
    
    Args:
        chat_id: The ID of the chat to retrieve messages for
        
    Returns:
        A list of messages
    """
    try:
        chat_obj = await sync_to_async(Chat.objects.get)(id=chat_id)
        
        # Get all messages for this chat
        messages_list = await sync_to_async(list)(Message.objects.filter(chat=chat_obj).values())
        
        return messages_list
    except Chat.DoesNotExist:
        return []


async def create_human_message(chat_id: Optional[str], message: str) -> HumanMessage:
    """
    Create a human message with the given chat ID and message.
    If chat_id is None or empty, a new chat will be created.
    For new chats, a subject will be generated based on the message content.

    Args:
        chat_id: The ID of the chat to create the message for, or None to create a new chat
        message: The message to create

    Returns:
        The created human message object
    """
    # Get or create the chat
    chat_obj = await get_or_create_chat(chat_id)
    
    # Create the human message
    human_message_obj = await sync_to_async(HumanMessage.objects.create)(
        chat=chat_obj,
        text=message
    )
    
    # If this is the first message in the chat and the chat has no subject,
    # generate a subject based on the message content
    message_count = await sync_to_async(Message.objects.filter(chat=chat_obj).count)()
    if message_count == 1 and not chat_obj.subject:
        # Generate a simple subject based on the first few words of the message
        # In a real implementation, you might want to use an LLM to generate a better subject
        words = message.split()
        subject = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
        chat_obj.subject = subject
        await sync_to_async(chat_obj.save)()
    
    return human_message_obj


async def create_bookedai_message(chat_id: Optional[str], message: str) -> BookedAIMessage:
    """
    Create a bookedai message with the given chat ID and message.
    If chat_id is None or empty, a new chat will be created.

    Args:
        chat_id: The ID of the chat to create the message for, or None to create a new chat
        message: The message to create

    Returns:
        The created bookedai message object
    """
    # Get or create the chat
    chat_obj = await get_or_create_chat(chat_id)
    
    # Create the bookedai message
    bookedai_message_obj = await sync_to_async(BookedAIMessage.objects.create)(
        chat=chat_obj,
        text=message
    )
    
    return bookedai_message_obj
