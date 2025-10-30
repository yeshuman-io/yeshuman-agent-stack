"""
Memory services for the agent.

Handles retrieval, classification, storage, and deduplication of user memories.
"""

import os
import time
import logging
from typing import Dict, List, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from apps.memories.backends import DjangoMemoryBackend

# Optional LangSmith tracing
try:
    from langsmith.run_helpers import traceable
except Exception:  # pragma: no cover
    def traceable(*args, **kwargs):  # type: ignore
        def _decorator(fn):
            return fn
        return _decorator

logger = logging.getLogger('agent')

# Simple per-user memory store state (rate limiting)
MEMORY_STATE: Dict[str, Dict[str, Any]] = {}

def _get_memory_state(user_id: str) -> Dict[str, Any]:
    if user_id not in MEMORY_STATE:
        MEMORY_STATE[user_id] = {
            "last_store_ts": 0.0,
            "stored_this_session": 0,
        }
    return MEMORY_STATE[user_id]


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.lower().strip().split())


def _hash_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


@traceable(name="memory.search", run_type="retriever")
async def retrieve_context_memories(user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve top-k relevant memories for a user query.

    Args:
        user_id: User identifier
        query: Search query text
        k: Number of memories to retrieve

    Returns:
        List of memory dicts with similarity scores
    """
    backend = DjangoMemoryBackend()
    result = await backend.search(query, user_id, limit=k)
    return result.get("results", [])


async def classify_should_store(text: str) -> Dict[str, Any]:
    """
    Classify if a user message should be stored as memory.

    Args:
        text: User message text

    Returns:
        Dict with keys: store (bool), reason (str), type (str)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured, skipping memory classification")
        return {"store": False, "reason": "API key not configured", "type": "other"}

    cls_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=api_key, streaming=False)
    prompt = SystemMessage(content=(
        "Decide if the following user message should be stored as a stable memory.\n"
        "Return strict JSON: {\"store\": bool, \"reason\": string, \"type\": one of [preference,identity,constraint,fact,other]}\n"
        "Criteria: store only user-specific, time-invariant facts or preferences; avoid greetings, ephemeral requests, transactional details."
    ))

    try:
        resp = await cls_llm.ainvoke([prompt, HumanMessage(content=text)])
        decision = {"store": False, "reason": "", "type": "other"}
        try:
            import json
            decision = json.loads(resp.content)
        except Exception as e:
            logger.warning(f"Failed to parse classification JSON: {e}")
        return decision
    except Exception as e:
        logger.error(f"Memory classification failed: {e}")
        return {"store": False, "reason": f"Classification error: {e}", "type": "other"}


@traceable(name="memory.store", run_type="tool")
async def store_memory(user_id: str, text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store a memory for a user.

    Args:
        user_id: User identifier
        text: Memory text content
        meta: Metadata dict with type, importance, etc.

    Returns:
        Dict with success status and memory_id
    """
    backend = DjangoMemoryBackend()
    messages = [{"role": "user", "content": text}]
    return await backend.add(messages, user_id, metadata=meta)


def recent_lru_check(user_id: str, text_hash: str, max_keep: int = 32) -> bool:
    """
    Check if text hash was seen recently (LRU cache).

    Args:
        user_id: User identifier
        text_hash: SHA256 hash of normalized text
        max_keep: Maximum hashes to keep per user

    Returns:
        True if hash was seen recently, False otherwise
    """
    # This would need to be made thread-safe for production
    # For now, using simple in-memory dict
    user_key = f"recent_{user_id}"
    if user_key not in globals():
        globals()[user_key] = []

    bucket = globals()[user_key]
    if text_hash in bucket:
        return True
    bucket.append(text_hash)
    if len(bucket) > max_keep:
        del bucket[0: len(bucket) - max_keep]
    return False


async def is_near_duplicate(user_id: str, text: str, threshold: float = 0.9, recent_n: int = 20) -> Tuple[bool, float]:
    """
    Check if text is a near-duplicate of recent user memories.

    Args:
        user_id: User identifier
        text: Text to check
        threshold: Similarity threshold (0-1)
        recent_n: Number of recent memories to check

    Returns:
        Tuple of (is_duplicate, max_similarity)
    """
    try:
        backend = DjangoMemoryBackend()
        # Use the backend's async method
        return await backend.is_near_duplicate(user_id, text, threshold, recent_n)
    except Exception as e:
        logger.error(f"Near-duplicate check failed: {e}")
        return False, 0.0


async def schedule_memory_storage(user_id: str, text: str, writer=None) -> None:
    """
    Schedule async memory storage with classification and deduplication.

    Args:
        user_id: User identifier
        text: User message text
        writer: Stream writer for SSE events (optional)
    """
    import asyncio

    async def _memory_store_task():
        try:
            logger.info("🧠 Memory storage task: started")

            # Rate limit check
            ms = _get_memory_state(user_id)
            now_ts = time.time()
            time_since_last = now_ts - ms["last_store_ts"]
            stored_count = ms["stored_this_session"]
            logger.info(f"🧠 Memory storage task: rate check - time_since_last={time_since_last:.1f}s, stored_this_session={stored_count}")

            if (time_since_last < 30) or (stored_count >= 3):
                logger.info("🧠 Memory storage task: rate limited, skipping")
                return

            # Classify
            decision = await classify_should_store(text)
            logger.info(f"🧠 Memory storage task: decision={decision}")

            if not decision.get("store", False):
                logger.info("🧠 Memory storage task: not storing (decision=false)")
                return

            # Dedup checks
            text_hash = _hash_text(text)
            if recent_lru_check(user_id, text_hash):
                logger.info("🧠 Memory storage task: skipping (recent duplicate)")
                return

            is_dup, max_sim = await is_near_duplicate(user_id, text, threshold=0.9)
            if is_dup:
                logger.info(f"🧠 Memory storage task: skipping (near duplicate, sim={max_sim:.2f})")
                return

            # Store
            meta = {
                "category": "general",
                "interaction_type": "conversation",
                "importance": "high" if decision.get("type") in ("preference","identity") else "medium",
                "source": "agent_entry",
                "type": decision.get("type", "other")
            }

            result = await store_memory(user_id, text, meta)

            # Update rate limiter
            ms["last_store_ts"] = now_ts
            ms["stored_this_session"] += 1

            # Emit SSE
            if writer:
                try:
                    from langchain_openai import ChatOpenAI
                    mini2 = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"), streaming=True)
                    sp = SystemMessage(content=(
                        "Generate a brief 1-line confirmation (<=10 words) that a useful memory was saved."
                    ))
                    summary_content = ""
                    async for _c in mini2.astream([sp]):
                        if _c.content:
                            summary_content = _c.content
                            writer({
                                "type": "memory",
                                "subType": "stored",
                                "content": _c.content,
                                "meta": {"stored": True}
                            })

                    # Also emit UI event for Labs to invalidate memories cache
                    if summary_content:
                        writer({
                            "type": "ui",
                            "entity": "memory",
                            "action": "stored",
                            "summary": summary_content,
                            "meta": {"stored": True}
                        })
                except Exception as e:
                    logger.warning(f"Memory stored SSE emission failed: {e}")

        except Exception as e:
            logger.error(f"Ambient memory store failed: {e}")

    asyncio.create_task(_memory_store_task())
