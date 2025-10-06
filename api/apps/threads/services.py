from django.db.models import QuerySet as DjangoQuerySet
from django.forms.models import model_to_dict
from asgiref.sync import sync_to_async
from typing import Optional, Tuple, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
import logging

from .models import Thread, Message, HumanMessage as HumanMessageModel, AssistantMessage

logger = logging.getLogger(__name__)


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


async def get_or_create_thread(user_id: Optional[str] = None, subject: Optional[str] = None, thread_id: Optional[str] = None, session_id: Optional[str] = None) -> Thread:
    """
    Get or create a thread with the given parameters.

    Supports both authenticated users and anonymous sessions.

    Args:
        user_id: The user ID to associate with the thread
        subject: The subject/title for the thread
        thread_id: The ID of the thread to get or create, or None to create a new thread
        session_id: Session ID for anonymous users

    Returns:
        The thread object
    """
    if thread_id:
        try:
            # Try to get the existing thread
            thread_obj = await sync_to_async(Thread.objects.get)(id=thread_id)
            return thread_obj
        except Thread.DoesNotExist:
            # Create a new thread with the specified ID
            is_anonymous = user_id is None and session_id is not None
            thread_obj = await sync_to_async(Thread.objects.create)(
                id=thread_id,
                user_id=user_id,
                session_id=session_id,
                subject=subject,
                is_anonymous=is_anonymous
            )
            # Mark as newly created for delta emission
            thread_obj._was_created = True
            return thread_obj
    else:
        # Create a new thread without specifying an ID
        is_anonymous = user_id is None and session_id is not None
        thread_obj = await sync_to_async(Thread.objects.create)(
            user_id=user_id,
            session_id=session_id,
            subject=subject,
            is_anonymous=is_anonymous
        )
        # Mark as newly created for delta emission
        thread_obj._was_created = True
        return thread_obj


async def get_all_thread_messages(thread_id: str, count_only: bool = False) -> List[dict]:
    """
    Get all messages for a given thread ID.

    Args:
        thread_id: The ID of the thread to retrieve messages for
        count_only: If True, return only the count instead of message list

    Returns:
        A list of message dictionaries or count
    """
    try:
        thread_obj = await sync_to_async(Thread.objects.get)(id=thread_id)

        if count_only:
            # Return count only
            count = await sync_to_async(Message.objects.filter(thread=thread_obj).count)()
            return count

        # Get all messages for this thread as objects, not dicts
        messages_list = await sync_to_async(list)(
            Message.objects.filter(thread=thread_obj).order_by('created_at')
        )
        return messages_list
    except Thread.DoesNotExist:
        return 0 if count_only else []


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
    thread_obj = await get_or_create_thread(user_id, None, thread_id)

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
    thread_obj = await get_or_create_thread(user_id, None, thread_id)

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


async def get_session_threads(session_id: str, limit: int = 50) -> List[Thread]:
    """
    Get all threads for a given session ID (anonymous users).

    Args:
        session_id: The session ID to get threads for
        limit: Maximum number of threads to return

    Returns:
        A list of thread objects
    """
    threads = await sync_to_async(list)(
        Thread.objects.filter(session_id=session_id).order_by('-updated_at')[:limit]
    )
    return threads


async def migrate_anonymous_thread_to_user(thread_id: str, user_id: str) -> bool:
    """
    Migrate an anonymous thread to belong to a user.

    Args:
        thread_id: The thread ID to migrate
        user_id: The user ID to assign ownership to

    Returns:
        True if migration successful, False otherwise
    """
    try:
        thread = await sync_to_async(Thread.objects.get)(id=thread_id, is_anonymous=True)
        thread.user_id = user_id
        thread.is_anonymous = False
        thread.session_id = None  # Clear session ID
        await sync_to_async(thread.save)()
        return True
    except Thread.DoesNotExist:
        return False


async def get_or_create_session_thread(session_id: str, subject: Optional[str] = None, thread_id: Optional[str] = None) -> Thread:
    """
    Get or create a thread for an anonymous session.

    Args:
        session_id: The session ID for the anonymous user
        subject: Optional subject for the thread
        thread_id: Optional specific thread ID to use

    Returns:
        The thread object
    """
    return await get_or_create_thread(
        user_id=None,
        subject=subject,
        thread_id=thread_id,
        session_id=session_id
    )


async def cleanup_old_anonymous_threads(days_old: int = 30) -> int:
    """
    Clean up old anonymous threads that haven't been updated recently.

    Args:
        days_old: Number of days old to consider for cleanup

    Returns:
        Number of threads cleaned up
    """
    from datetime import timedelta
    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=days_old)

    # Delete old anonymous threads
    deleted_count = await sync_to_async(
        lambda: Thread.objects.filter(
            is_anonymous=True,
            updated_at__lt=cutoff_date
        ).delete()
    )()

    return deleted_count[0] if isinstance(deleted_count, tuple) else deleted_count


async def should_generate_thread_title(thread_id: str) -> bool:
    """
    Determine if a thread has enough messages to warrant LLM-based title generation.

    Args:
        thread_id: The thread ID to check

    Returns:
        True if thread should get LLM-generated title
    """
    try:
        thread = await get_thread(thread_id)
        if not thread:
            return False

        # Don't rename if already has a custom title
        if thread.subject and not thread.subject.startswith(('Conversation', 'Anonymous', 'Untitled')):
            return False

        # Count messages
        message_count = await sync_to_async(Message.objects.filter(thread=thread).count)()

        # Need at least 3 messages for meaningful context
        return message_count >= 3

    except Exception as e:
        logger.warning(f"Error checking thread title generation eligibility: {e}")
        return False


async def generate_thread_title_with_llm(thread_id: str) -> Optional[str]:
    """
    Generate a 2-5 word thread title using LLM analysis of conversation content.

    Args:
        thread_id: The thread ID to generate title for

    Returns:
        Generated title string or None if generation fails
    """
    try:
        from langchain_openai import ChatOpenAI
        from django.conf import settings

        # Get recent messages for context (last 6 messages should be sufficient)
        messages = await sync_to_async(list)(
            Message.objects.filter(thread_id=thread_id).order_by('-created_at')[:6]
        )
        messages.reverse()  # Put in chronological order

        if len(messages) < 3:
            return None

        # Format conversation for LLM
        conversation_parts = []
        for msg in messages:
            msg_type = "Human" if isinstance(msg, HumanMessageModel) else "Assistant"
            conversation_parts.append(f"{msg_type}: {msg.text[:200]}")  # Truncate long messages

        conversation_text = "\n".join(conversation_parts)

        # Create LLM prompt
        prompt = f"""Analyze this conversation and create a concise title (2-5 words) that captures the main topic or purpose.

Guidelines:
- Focus on the core question, problem, or topic
- Use specific, descriptive language
- Keep it very brief (2-5 words maximum)
- Avoid generic titles like "General Discussion" or "Help Request"

Conversation:
{conversation_text}

Title:"""

        # Call OpenAI
        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=20  # Very short response needed
        )

        response = await llm.ainvoke(prompt)
        title = response.content.strip()

        # Validate and clean up
        words = title.split()
        if 2 <= len(words) <= 5:
            # Capitalize first letter of each word
            cleaned_title = " ".join(word.capitalize() for word in words)
            return cleaned_title

        logger.warning(f"LLM generated invalid title length: '{title}' ({len(words)} words)")
        return None

    except Exception as e:
        logger.error(f"Error generating thread title with LLM: {e}")
        return None


async def update_thread_title(thread_id: str, title: str) -> bool:
    """
    Update a thread's title and emit UI delta.

    Args:
        thread_id: Thread to update
        title: New title

    Returns:
        True if successful
    """
    try:
        thread = await get_thread(thread_id)
        if not thread:
            return False

        thread.subject = title
        await sync_to_async(thread.save)()

        logger.info(f"✅ [THREAD TITLE] Updated thread {thread_id} title to: '{title}'")
        return True

    except Exception as e:
        logger.error(f"Error updating thread title: {e}")
        return False


async def handle_thread_title_generation(thread_id: str):
    """
    Handle the complete thread title generation process including UI deltas.

    Args:
        thread_id: Thread to process
    """
    try:
        # Check if we should generate a title
        if not await should_generate_thread_title(thread_id):
            return

        logger.info(f"🎯 [THREAD TITLE] Starting LLM title generation for thread {thread_id}")

        # Emit "generating" delta for UI feedback
        # This will be yielded from the streaming endpoint that calls this
        # For now, we'll handle this in the calling code

        # Generate title
        title = await generate_thread_title_with_llm(thread_id)

        if title:
            # Update thread title
            success = await update_thread_title(thread_id, title)
            if success:
                logger.info(f"✅ [THREAD TITLE] Successfully generated and saved title: '{title}'")
            else:
                logger.warning(f"❌ [THREAD TITLE] Failed to save generated title: '{title}'")
        else:
            logger.warning(f"❌ [THREAD TITLE] LLM failed to generate valid title for thread {thread_id}")

    except Exception as e:
        logger.error(f"Error in thread title generation process: {e}")
