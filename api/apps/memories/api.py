"""
API endpoints for memories app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List, Optional
from apps.memories.models import Memory, MemorySearch, MemoryPattern

# Create router for memories endpoints
memories_router = Router()


class MemorySchema(Schema):
    """Schema for Memory model."""
    id: str
    user_id: str
    content: str
    memory_type: str
    interaction_type: str
    category: str
    subcategory: str
    importance: str
    created_at: str


class MemoryCreateSchema(Schema):
    """Schema for creating a Memory."""
    user_id: str
    content: str
    memory_type: str = "factual"
    category: str
    subcategory: str = ""
    importance: str = "medium"


@memories_router.get("/", response=List[MemorySchema], tags=["Memories"])
async def list_memories(request, user_id: Optional[str] = None):
    """List memories, optionally filtered by user_id."""
    from asgiref.sync import sync_to_async

    def get_memories():
        queryset = Memory.objects.all()
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return list(queryset)

    memories = await sync_to_async(get_memories)()

    return [
        MemorySchema(
            id=str(memory.id),
            user_id=memory.user_id,
            content=memory.content,
            memory_type=memory.memory_type,
            interaction_type=memory.interaction_type,
            category=memory.category,
            subcategory=memory.subcategory,
            importance=memory.importance,
            created_at=memory.created_at.isoformat()
        )
        for memory in memories
    ]


@memories_router.post("/", response=MemorySchema, tags=["Memories"])
async def create_memory(request, payload: MemoryCreateSchema):
    """Create a new memory."""
    from asgiref.sync import sync_to_async

    memory = await sync_to_async(Memory.objects.create)(
        user_id=payload.user_id,
        content=payload.content,
        memory_type=payload.memory_type,
        category=payload.category,
        subcategory=payload.subcategory,
        importance=payload.importance
    )

    # Generate embedding if possible
    try:
        await sync_to_async(memory.ensure_embedding)()
    except Exception:
        # Continue without embedding if it fails
        pass

    return MemorySchema(
        id=str(memory.id),
        user_id=memory.user_id,
        content=memory.content,
        memory_type=memory.memory_type,
        interaction_type=getattr(memory, 'interaction_type', 'conversation'),
        category=memory.category,
        subcategory=getattr(memory, 'subcategory', ''),
        importance=getattr(memory, 'importance', 'medium'),
        created_at=memory.created_at.isoformat()
    )


@memories_router.get("/{memory_id}", response={200: MemorySchema, 404: dict}, tags=["Memories"])
async def get_memory(request, memory_id: str):
    """Get a specific memory by ID."""
    from asgiref.sync import sync_to_async

    try:
        memory = await sync_to_async(Memory.objects.get)(id=memory_id)
        return 200, MemorySchema(
            id=str(memory.id),
            user_id=memory.user_id,
            content=memory.content,
            memory_type=memory.memory_type,
            interaction_type=getattr(memory, 'interaction_type', 'conversation'),
            category=memory.category,
            subcategory=getattr(memory, 'subcategory', ''),
            importance=getattr(memory, 'importance', 'medium'),
            created_at=memory.created_at.isoformat()
        )
    except Memory.DoesNotExist:
        return 404, {"error": "Memory not found"}
