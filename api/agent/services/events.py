"""
Event services for the agent.

Handles SSE event emission for memory and tool operations.
"""

import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

logger = logging.getLogger('agent')


async def emit_memory_retrieved(writer, count: int, top_similarity: float = None) -> None:
    """
    Emit SSE event for memory retrieval.

    Args:
        writer: Stream writer function
        count: Number of memories retrieved
        top_similarity: Top similarity score (optional)
    """
    if not writer or count == 0:
        return

    try:
        mini = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"), streaming=True)
        summary_prompt = SystemMessage(content=(
            "Generate a brief 1-line status (<=12 words) summarizing memory retrieval for the user's request. "
            "Example: 'Found 3 relevant memories about travel preferences.'"
        ))
        async for _chunk in mini.astream([summary_prompt]):
            if _chunk.content:
                writer({
                    "type": "memory",
                    "subType": "retrieved",
                    "content": _chunk.content,
                    "meta": {
                        "count": count,
                        "top_similarity": top_similarity,
                    }
                })
    except Exception as e:
        logger.warning(f"Memory retrieved SSE emission failed: {e}")


async def emit_memory_stored(writer, summary: str = None) -> None:
    """
    Emit SSE event for memory storage.

    Args:
        writer: Stream writer function
        summary: Pre-generated summary or None to generate
    """
    if not writer:
        return

    try:
        if summary:
            writer({
                "type": "memory",
                "subType": "stored",
                "content": summary,
                "meta": {"stored": True}
            })
            return

        # Generate summary
        mini2 = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"), streaming=True)
        sp = SystemMessage(content=(
            "Generate a brief 1-line confirmation (<=10 words) that a useful memory was saved."
        ))
        async for _c in mini2.astream([sp]):
            if _c.content:
                writer({
                    "type": "memory",
                    "subType": "stored",
                    "content": _c.content,
                    "meta": {"stored": True}
                })
    except Exception as e:
        logger.warning(f"Memory stored SSE emission failed: {e}")


def emit_tool_start(writer, tool_names: list) -> None:
    """Emit tool start event."""
    if writer:
        writer({"type": "tool", "content": f"🔧 Calling tools: {', '.join(tool_names)}"})


def emit_tool_complete(writer, tool_names: list) -> None:
    """Emit tool complete event."""
    if writer:
        writer({"type": "tool_complete", "content": f"✅ Completed tools: {', '.join(tool_names)}"})
