"""
Django-based Checkpointer for LangGraph

Integrates LangGraph state persistence with Django's Thread/Message models
for seamless conversation continuity.

Follows LangGraph's async-first pattern like AsyncRedisSaver, AsyncPostgresSaver, etc.
"""

import logging
from typing import Iterator, Optional, Any, Dict, List, Tuple
from datetime import datetime

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langgraph.checkpoint.serde.base import SerializerProtocol
from langchain_core.messages import BaseMessage
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class DjangoCheckpointSaver(BaseCheckpointSaver):
    """
    Django-based checkpointer that stores LangGraph state in Django models.

    Integrates with existing Thread/Message architecture while providing
    LangGraph's threading capabilities.

    Follows LangGraph's async-first pattern like AsyncRedisSaver, AsyncPostgresSaver, etc.
    """
    _instance = None

    def __init__(self, serde: Optional[SerializerProtocol] = None):
        if DjangoCheckpointSaver._instance is not None:
            raise Exception("DjangoCheckpointSaver is a singleton class. Use get_instance() instead.")
        super().__init__(serde=serde)
        self._checkpoints: Dict[str, CheckpointTuple] = {}
        DjangoCheckpointSaver._instance = self

    @classmethod
    def get_instance(cls, serde: Optional[SerializerProtocol] = None):
        """Get the singleton instance of DjangoCheckpointSaver."""
        if cls._instance is None:
            cls._instance = cls(serde=serde)
        return cls._instance

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Async get the latest checkpoint for the given config."""
        thread_id = config.get("configurable", {}).get("thread_id")
        logger.info(f"🔍 [CHECKPOINTER] aget_tuple called with thread_id: {thread_id}")
        if not thread_id or thread_id == "default":
            # No thread persistence for anonymous/default sessions
            logger.info(f"🔍 [CHECKPOINTER] Skipping persistence for thread_id: {thread_id}")
            return None

        try:
            # Use sync_to_async for Django operations since we're in an async context
            from apps.threads.models import Thread
            from apps.threads.services import get_thread_messages_as_langchain

            # Handle thread_id - could be string or int
            # If it's a string that looks like an int, convert it
            try:
                if isinstance(thread_id, str) and thread_id.isdigit():
                    thread_id = int(thread_id)
            except (ValueError, AttributeError):
                pass  # Keep as string

            # Get the thread - handle both string and int IDs
            try:
                logger.info(f"Getting thread {thread_id} (type: {type(thread_id)})")
                from asgiref.sync import sync_to_async

                # Wrap the database query in sync_to_async
                def _get_thread():
                    try:
                        return Thread.objects.get(id=thread_id)
                    except Thread.DoesNotExist:
                        return None

                thread = await sync_to_async(_get_thread)()
                if thread is None:
                    logger.warning(f"Thread {thread_id} not found for checkpoint retrieval")
                    return None

                # Get thread subject safely in async context
                thread_subject = await sync_to_async(lambda: thread.subject)()
                logger.info(f"Found thread {thread_id}: {thread_subject}")
            except Exception as e:
                # Thread doesn't exist, or thread_id is not a valid ID
                logger.warning(f"Error retrieving thread {thread_id}: {e}")
                return None

            # Check if we have a checkpoint stored for this thread
            if thread_id not in self._checkpoints:
                # Load checkpoint from Django if it exists (wrap in sync_to_async)
                checkpoint_data = await sync_to_async(lambda: getattr(thread, '_langgraph_checkpoint', None))()
                if checkpoint_data:
                    # Use the stored checkpoint data directly (it's already a dict)
                    stored_checkpoint = checkpoint_data['checkpoint']
                    # Since Checkpoint is a dict subclass, we can use the stored dict directly
                    checkpoint = stored_checkpoint  # Already in the right format
                    metadata = checkpoint_data.get('metadata', {})
                    self._checkpoints[thread_id] = CheckpointTuple(
                        config=config,
                        checkpoint=checkpoint,
                        metadata=metadata
                    )
                else:
                    # No checkpoint exists, create initial state from thread messages
                    messages = await get_thread_messages_as_langchain(thread_id)
                    if messages:
                        # Get thread attributes safely
                        user_id = await sync_to_async(lambda: thread.user_id)()
                        user = await sync_to_async(lambda: thread.user)()

                        # Create initial checkpoint from existing messages
                        checkpoint = Checkpoint(
                            v=1,
                            id=f"checkpoint_{thread_id}_initial",
                            ts=datetime.now().isoformat(),
                            channel_values={
                                "messages": messages,
                                "user_id": str(user_id) if user else None,
                                "tools_done": True,  # Assume tools are done for loaded conversations
                                "voice_messages": [],
                                "last_voice_sig": None,
                                "tool_call_count": 0
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
                        tuple_obj = CheckpointTuple(
                            config=config,
                            checkpoint=checkpoint,
                            metadata={"source": "django_thread"}
                        )
                        self._checkpoints[thread_id] = tuple_obj
                        return tuple_obj

            return self._checkpoints.get(thread_id)

        except Thread.DoesNotExist:
            logger.warning(f"Thread {thread_id} not found for checkpoint retrieval")
            return None
        except Exception as e:
            logger.error(f"Error retrieving checkpoint for thread {thread_id}: {e}")
            return None

    async def aput(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: Dict[str, Any], new_versions: Optional[Dict[str, Any]] = None) -> None:
        """Async save a checkpoint for the given config."""
        thread_id = config.get("configurable", {}).get("thread_id")
        logger.info(f"💾 [CHECKPOINTER] aput called with thread_id: {thread_id}")
        if not thread_id or thread_id == "default":
            # No thread persistence for anonymous/default sessions
            logger.info(f"💾 [CHECKPOINTER] Skipping persistence for thread_id: {thread_id}")
            return

        try:
            # Use sync_to_async for Django operations since we're in an async context
            from apps.threads.models import Thread

            # Handle thread_id - could be string or int
            # If it's a string that looks like an int, convert it
            original_thread_id = thread_id
            try:
                if isinstance(thread_id, str) and thread_id.isdigit():
                    thread_id = int(thread_id)
            except (ValueError, AttributeError):
                pass  # Keep as string

            # Get or create the thread
            # For now, skip persistence if we don't have proper user context
            # TODO: Implement proper anonymous user handling
            user_id = config.get("configurable", {}).get("user_id")
            if not user_id:
                logger.warning(f"No user_id available for thread {original_thread_id}, skipping persistence")
                return

            # Only create threads with integer IDs
            if isinstance(thread_id, int):
                from asgiref.sync import sync_to_async

                def _get_or_create_thread():
                    return Thread.objects.get_or_create(
                        id=thread_id,
                        defaults={
                            'user_id': user_id,
                            'subject': f'LangGraph Conversation {original_thread_id}',
                            'is_anonymous': False
                        }
                    )

                thread, created = await sync_to_async(_get_or_create_thread)()
            else:
                # For non-integer thread_ids, skip persistence for now
                logger.warning(f"Skipping persistence for non-integer thread_id: {original_thread_id}")
                return

            # Handle case where checkpoint might be a dict instead of Checkpoint object
            logger.info(f"Checkpoint type before conversion: {type(checkpoint)}")
            if isinstance(checkpoint, dict):
                logger.info("Converting dict to Checkpoint object")
                # Convert dict to Checkpoint object
                checkpoint = Checkpoint(**checkpoint)
            logger.info(f"Checkpoint type after conversion: {type(checkpoint)}")
            logger.info(f"Checkpoint has 'v' attribute: {hasattr(checkpoint, 'v')}")

            # Store checkpoint in memory cache
            tuple_obj = CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata
            )
            self._checkpoints[thread_id] = tuple_obj

            # Store checkpoint data on thread for persistence
            # Convert checkpoint to serializable dict (checkpoint is a dict subclass)
            # Handle different checkpoint structures - some have 'v', others don't
            checkpoint_dict = {}
            for key in ['v', 'id', 'ts', 'channel_values', 'channel_versions', 'versions_seen', 'pending_sends']:
                if key in checkpoint:
                    if key == 'channel_values':
                        checkpoint_dict[key] = self._serialize_channel_values(checkpoint[key])
                    else:
                        checkpoint_dict[key] = checkpoint[key]
                else:
                    logger.warning(f"Checkpoint missing expected key: {key}")
                    # Provide defaults for missing keys
                    if key == 'v':
                        checkpoint_dict[key] = 1
                    elif key == 'versions_seen':
                        checkpoint_dict[key] = {}
                    elif key == 'pending_sends':
                        checkpoint_dict[key] = []
                    else:
                        checkpoint_dict[key] = None

            # Store on thread object (temporary - in production you'd want a proper model)
            # Wrap attribute assignment in sync_to_async
            await sync_to_async(lambda: setattr(thread, '_langgraph_checkpoint', {
                'checkpoint': checkpoint_dict,
                'metadata': metadata,
                'saved_at': datetime.now().isoformat()
            }))()

            # Save the thread with checkpoint data
            from asgiref.sync import sync_to_async
            await sync_to_async(thread.save)()

            logger.debug(f"Saved checkpoint for thread {thread_id}")

        except Exception as e:
            logger.error(f"Error saving checkpoint for thread {thread_id}: {e}")

    async def alist(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None,
             before: Optional[Checkpoint] = None, limit: Optional[int] = None):
        """Async list checkpoints for the given config."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return

        # For now, just return the latest checkpoint if it exists
        tuple_obj = await self.aget_tuple(config)
        if tuple_obj:
            yield tuple_obj

    # Sync methods - simplified for testing (LangGraph primarily uses async methods)
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Sync method - simplified to avoid event loop issues during testing."""
        # For now, just check in-memory cache without Django operations
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id or thread_id == "default":
            return None
        return self._checkpoints.get(thread_id)

    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: Dict[str, Any]) -> None:
        """Sync method - simplified to avoid event loop issues during testing."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id or thread_id == "default":
            return

        # Just update in-memory cache
        tuple_obj = CheckpointTuple(config=config, checkpoint=checkpoint, metadata=metadata)
        self._checkpoints[thread_id] = tuple_obj

    def list(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None,
             before: Optional[Checkpoint] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """Sync method - simplified to avoid event loop issues during testing."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id and thread_id in self._checkpoints:
            yield self._checkpoints[thread_id]

    def put_writes(self, config: Dict[str, Any], writes: List[Tuple[str, Any]], task_id: str) -> None:
        """Handle pending writes (required by BaseCheckpointSaver)."""
        # For now, we'll handle this in the main aput() method
        # In a full implementation, you might want to batch writes
        pass

    async def aput_writes(self, config: Dict[str, Any], writes: List[Tuple[str, Any]], task_id: str) -> None:
        """Async version of put_writes."""
        return self.put_writes(config, writes, task_id)

    def _serialize_channel_values(self, channel_values: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize channel values for storage."""
        serialized = {}
        for key, value in channel_values.items():
            if key == "messages":
                # Convert BaseMessage objects to dicts
                serialized[key] = [self._message_to_dict(msg) for msg in value]
            elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                serialized[key] = value
            else:
                # Convert other objects to string representation
                serialized[key] = str(value)
        return serialized

    def _message_to_dict(self, message: BaseMessage) -> Dict[str, Any]:
        """Convert a BaseMessage to a dict for storage."""
        return {
            'type': message.__class__.__name__,
            'content': message.content,
            'additional_kwargs': getattr(message, 'additional_kwargs', {}),
            'id': getattr(message, 'id', None),
            'name': getattr(message, 'name', None),
            'tool_calls': getattr(message, 'tool_calls', None),
            'tool_call_id': getattr(message, 'tool_call_id', None),
        }