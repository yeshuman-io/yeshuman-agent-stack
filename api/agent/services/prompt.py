"""
Prompt services for the agent.

Handles system prompt retrieval and memory injection.
"""

import logging
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage

logger = logging.getLogger('agent')

# Initialize with fallback, will be updated when Django is ready
_SYSTEM_PROMPT = None

def get_fallback_prompt():
    """Fallback system prompt when Django settings unavailable."""
    return """You are an AI assistant without a name.

Address the user as "Human" or "human".
Don't use synonyms "human".
Use different punctuations for "yes" and "human" such as ' ! , . ; ?.
Subtly borrow terminology and language patterns from Blade Runner and Dune without directly referencing these works by name.
Be subtle, don't over do it.  Be minimal and slightly robotic.  Be dead pan without exclamations."""


def get_system_prompt():
    """Get the system prompt for the current client configuration."""
    global _SYSTEM_PROMPT

    # Try to refresh system prompt from Django settings if available
    try:
        from django.conf import settings
        # Check if settings are configured
        if hasattr(settings, 'CURRENT_CLIENT'):
            current_prompt = settings.CURRENT_CLIENT['system_prompt']
            if current_prompt != _SYSTEM_PROMPT:
                _SYSTEM_PROMPT = current_prompt
                logger.debug("Updated system prompt for client configuration")
            return _SYSTEM_PROMPT
        else:
            # Django settings not fully loaded yet
            return get_fallback_prompt()
    except (ImportError, AttributeError):
        # Django not available or not configured
        return get_fallback_prompt()


def inject_memories_into_prompt(base_prompt: str, memories: List[Dict[str, Any]]) -> str:
    """
    Inject relevant memories into the system prompt.

    Args:
        base_prompt: Base system prompt text
        memories: List of memory dicts with content/similarity

    Returns:
        Enhanced prompt with memories section
    """
    if not memories:
        return base_prompt

    # Check if memories are already included (avoid duplication)
    if "## Relevant Memories" in base_prompt:
        return base_prompt

    memory_section = "\n\n## Relevant Memories\n"
    for i, mem in enumerate(memories[:3], 1):  # Limit to top 3
        content = mem.get("memory", mem.get("content", ""))[:200]  # Try both keys
        similarity = mem.get("metadata", {}).get("similarity", 0)
        memory_section += f"{i}. {content}\n"

    return base_prompt + memory_section
