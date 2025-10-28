"""
LangSmith tracing utilities for conversation-level tracing.

Provides async-first utilities to manage conversation root traces and child runs,
enabling proper parent-child relationships in LangSmith for multi-turn conversations.
"""

import os
import logging
from typing import Optional, Dict, List, Any
from uuid import UUID
from contextlib import asynccontextmanager

from langsmith import trace
from langsmith.run_helpers import tracing_context

logger = logging.getLogger(__name__)


async def get_or_create_conversation_root(thread_id: str, user) -> UUID:
    """
    Get or create a conversation root trace for a thread.

    This creates a persistent root run that serves as the parent for all turns
    in a conversation, enabling conversation-level visibility in LangSmith.

    Args:
        thread_id: The thread/conversation identifier
        user: Django user object (can be None for anonymous)

    Returns:
        UUID of the root trace (same as the root run ID)
    """
    from apps.threads.models import Thread
    from asgiref.sync import sync_to_async

    logger.info(f"🔗 Getting/creating root trace for thread: {thread_id}")

    # Get thread (handle both string and int IDs)
    try:
        if isinstance(thread_id, str) and thread_id.isdigit():
            thread_id_int = int(thread_id)
        else:
            thread_id_int = thread_id
        thread = await sync_to_async(Thread.objects.get)(id=thread_id_int)
    except Thread.DoesNotExist:
        logger.warning(f"Thread {thread_id} not found for root trace creation")
        raise ValueError(f"Thread {thread_id} does not exist")

    # If root trace already exists, return it
    if thread.langsmith_trace_id:
        logger.info(f"🔗 Found existing root trace: {thread.langsmith_trace_id}")
        return thread.langsmith_trace_id

    # Create new root trace
    logger.info(f"🔗 Creating new root trace for thread: {thread_id}")

    user_id = str(user.id) if user else "anonymous"
    project_name = os.getenv("LANGCHAIN_PROJECT", "lumie-agent")

    # Create the root conversation trace
    async with trace(
        name="conversation",
        run_type="chain",
        project_name=project_name,
        metadata={
            "thread_id": thread_id,
            "conversation_id": thread_id,
            "user_id": user_id,
            "is_root": True
        },
        tags=[
            f"thread_{thread_id}",
            f"user_{user_id}",
            "conversation_root"
        ]
    ) as root_run:
        root_trace_id = root_run.id
        logger.info(f"🔗 Created root trace: {root_trace_id}")

        # Save to thread
        await sync_to_async(lambda: setattr(thread, 'langsmith_trace_id', root_trace_id))()
        await sync_to_async(thread.save)()
        logger.info(f"🔗 Saved root trace {root_trace_id} to thread {thread_id}")

        return root_trace_id


@asynccontextmanager
async def with_conversation_parent(root_trace_id: UUID):
    """
    Context manager to set the parent trace for a conversation turn.

    All LangSmith operations within this context will be child runs
    of the specified root trace.

    Args:
        root_trace_id: UUID of the conversation root trace
    """
    logger.info(f"🔗 Setting parent context to root trace: {root_trace_id}")

    # Use asyncio.to_thread to run the synchronous context manager in a thread
    import asyncio

    # We need to create an async wrapper that can run the sync context manager
    # and keep it alive for the duration of our async context
    context_active = True

    def _run_context_manager():
        """Run the synchronous context manager in a separate thread."""
        with tracing_context(distributed_parent_id=str(root_trace_id)):
            # Wait until the context is no longer needed
            import time
            while context_active:
                time.sleep(0.01)  # Small sleep to avoid busy waiting

    # Start the context manager in a thread
    context_task = asyncio.create_task(asyncio.to_thread(_run_context_manager))

    try:
        yield
    finally:
        # Signal the context manager to exit
        context_active = False
        # Wait for the context task to complete
        try:
            await asyncio.wait_for(context_task, timeout=1.0)
        except asyncio.TimeoutError:
            context_task.cancel()

    logger.debug(f"🔗 Exited parent context for root trace: {root_trace_id}")



def build_metadata(thread_id: str, user, turn_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Build consistent metadata for LangSmith runs.

    Args:
        thread_id: The conversation thread identifier
        user: Django user object
        turn_index: Optional turn number in the conversation

    Returns:
        Dict of metadata for LangSmith
    """
    metadata = {
        "session_id": thread_id,  # Groups runs by conversation
        "conversation_id": thread_id,
        "user_id": str(user.id) if user else "anonymous"
    }

    if turn_index is not None:
        metadata["turn_index"] = turn_index

    return metadata


def build_tags(thread_id: str, user) -> List[str]:
    """
    Build consistent tags for LangSmith runs.

    Args:
        thread_id: The conversation thread identifier
        user: Django user object

    Returns:
        List of tags for LangSmith
    """
    user_id = str(user.id) if user else "anonymous"

    return [
        f"thread_{thread_id}",
        f"user_{user_id}",
        "conversation_turn"
    ]


def resolve_trace_id(run_tree) -> str:
    """
    Extract the trace_id from a LangSmith run tree.

    For conversation-level tracing, we want the trace_id (root)
    rather than the individual run id (child).

    Args:
        run_tree: LangSmith run tree object

    Returns:
        String representation of the trace ID
    """
    trace_id = getattr(run_tree, 'trace_id', None) or getattr(run_tree, 'id', None)
    if trace_id is None:
        raise ValueError("Could not resolve trace_id from run_tree")

    return str(trace_id)
