from django.db.models import QuerySet as DjangoQuerySet
from django.forms.models import model_to_dict
from asgiref.sync import sync_to_async
from typing import Optional, Tuple, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .models import Thread, Message, HumanMessage as HumanMessageModel, AssistantMessage


async def get_thread(thread_id: str) -> Optional[Thread]:
    """
    Get a thread with the given ID.

    Args:
        thread_id: The ID of the thread to get

    Returns:
        The thread object, or None if the thread does not exist
    """
    try:
        return await sync_to_async(Thread.objects.get)(id=thread_id)
    except Thread.DoesNotExist:
        return None


async def get_or_create_thread(thread_id: Optional[str] = None, user_id: Optional[str] = None) -> Thread:
    """
    Get or create a thread with the given ID.

    If thread_id is None or empty, a new thread will be created.
    If thread_id is provided and exists, the existing thread will be returned.
    If thread_id is provided but doesn't exist, a new thread with that ID will be created.

    Args:
        thread_id: The ID of the thread to get or create, or None to create a new thread
        user_id: The user ID to associate with the thread

    Returns:
        The thread object
    """
    if not thread_id:
        # Create a new thread without specifying an ID
        thread_obj = await sync_to_async(Thread.objects.create)(user_id=user_id)
        return thread_obj

    try:
        # Try to get the existing thread
        thread_obj = await sync_to_async(Thread.objects.get)(id=thread_id)
        return thread_obj
    except Thread.DoesNotExist:
        # Create a new thread with the specified ID
        thread_obj = await sync_to_async(Thread.objects.create)(id=thread_id, user_id=user_id)
        return thread_obj


async def get_all_thread_messages(thread_id: str) -> List[dict]:
    """
    Get all messages for a given thread ID.

    Args:
        thread_id: The ID of the thread to retrieve messages for

    Returns:
        A list of message dictionaries
    """
    try:
        thread_obj = await sync_to_async(Thread.objects.get)(id=thread_id)

        # Get all messages for this thread
        messages_list = await sync_to_async(list)(Message.objects.filter(thread=thread_obj).values())
        return messages_list
    except Thread.DoesNotExist:
        return []


async def get_thread_messages_as_langchain(thread_id: str) -> List:
    """
    Get all messages for a thread formatted as LangChain message objects.

    Args:
        thread_id: The ID of the thread to retrieve messages for

    Returns:
        A list of LangChain message objects
    """
    try:
        thread_obj = await sync_to_async(Thread.objects.get)(id=thread_id)
        messages = []

        # Get all messages for this thread
        message_objects = await sync_to_async(list)(
            Message.objects.filter(thread=thread_obj).order_by('created_at')
        )

        for msg in message_objects:
            if isinstance(msg, HumanMessageModel):
                messages.append(HumanMessage(content=msg.text))
            elif isinstance(msg, AssistantMessage):
                messages.append(AIMessage(content=msg.text))
            # Add other message types as needed

        return messages
    except Thread.DoesNotExist:
        return []


async def create_human_message(thread_id: Optional[str], message: str, user_id: Optional[str] = None) -> HumanMessageModel:
    """
    Create a human message with the given thread ID and message.
    If thread_id is None or empty, a new thread will be created.
    For new threads, a subject will be generated based on the message content.

    Args:
        thread_id: The ID of the thread to create the message for, or None to create a new thread
        message: The message to create
        user_id: The user ID to associate with the thread

    Returns:
        The created human message object
    """
    # Get or create the thread
    thread_obj = await get_or_create_thread(thread_id, user_id)

    # Create the human message
    human_message_obj = await sync_to_async(HumanMessageModel.objects.create)(
        thread=thread_obj,
        text=message
    )

    # If this is the first message in the thread and the thread has no subject,
    # generate a simple subject based on the message content
    message_count = await sync_to_async(Message.objects.filter(thread=thread_obj).count)()
    if message_count == 1 and not thread_obj.subject:
        # Generate a simple subject based on the first few words of the message
        words = message.split()
        subject = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
        thread_obj.subject = subject
        await sync_to_async(thread_obj.save)()

    return human_message_obj


async def create_assistant_message(thread_id: Optional[str], message: str, user_id: Optional[str] = None) -> AssistantMessage:
    """
    Create an assistant message with the given thread ID and message.
    If thread_id is None or empty, a new thread will be created.

    Args:
        thread_id: The ID of the thread to create the message for, or None to create a new thread
        message: The message to create
        user_id: The user ID to associate with the thread

    Returns:
        The created assistant message object
    """
    # Get or create the thread
    thread_obj = await get_or_create_thread(thread_id, user_id)

    # Create the assistant message
    assistant_message_obj = await sync_to_async(AssistantMessage.objects.create)(
        thread=thread_obj,
        text=message
    )

    return assistant_message_obj


async def get_user_threads(user_id: str, limit: int = 50) -> List[Thread]:
    """
    Get all threads for a given user ID.

    Args:
        user_id: The user ID to get threads for
        limit: Maximum number of threads to return

    Returns:
        A list of thread objects
    """
    threads = await sync_to_async(list)(
        Thread.objects.filter(user_id=user_id).order_by('-updated_at')[:limit]
    )
    return threads
