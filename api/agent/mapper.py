"""
Tool Event Mapping System

Maps tools to UI events for real-time interface updates.
Only agent-driven tool executions emit UI events.
Manual UI/API operations use standard response handling.
"""

from typing import Dict, Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

# Tool to UI Event Mappings
# Only tools that modify data and should trigger UI updates are included
TOOL_EVENT_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # Profile Management Tools
    "manage_user_profile": {
        "entity": "profile",
        "action": "updated",
        "entity_id_extractor": lambda tool_call, result, user_id: f"user_{user_id}",
        "description": "User profile managed by agent",
        "always_navigate": "/profile"  # Always navigate to profile page for profile tools
    },

    # Legacy mapping (deprecated - replaced by manage_user_profile)
    "update_user_profile": {
        "entity": "profile",
        "action": "updated",
        "entity_id_extractor": lambda tool_call, result, user_id: f"user_{user_id}",
        "description": "User profile updated by agent"
    },

    # COMMENTED OUT FOR FOCUSED TESTING - Only UpdateUserProfileTool active
    # "create_profile": {
    #     "entity": "profile",
    #     "action": "created",
    #     "success_check": lambda result: isinstance(result, str) and "successfully" in result.lower(),
    #     "entity_id_extractor": lambda tool_call, result, user_id: extract_profile_id_from_result(result) or f"user_{user_id}",
    #     "description": "New profile created by agent"
    # },

    # "update_profile": {
    #     "entity": "profile",
    #     "action": "updated",
    #     "success_check": lambda result: isinstance(result, str) and "successfully" in result.lower(),
    #     "entity_id_extractor": lambda tool_call, result, user_id: extract_profile_id_from_tool_call(tool_call) or f"user_{user_id}",
    #     "description": "Existing profile updated by agent"
    # },

    # Future: Application tools
    # "create_application": {...},
    # "change_application_stage": {...},

    # Organisation Management Tools
    "create_organisation": {
        "entity": "organisation",
        "action": "created",
        "success_check": lambda result: isinstance(result, dict) and result.get("success") == True,
        "entity_id_extractor": lambda tool_call, result, user_id: result.get("organisation", {}).get("slug", "unknown"),
        "description": "Organisation created by agent"
    },

    "update_organisation": {
        "entity": "organisation",
        "action": "updated",
        "success_check": lambda result: isinstance(result, dict) and result.get("success") == True,
        "entity_id_extractor": lambda tool_call, result, user_id: result.get("organisation", {}).get("slug", "unknown"),
        "description": "Organisation updated by agent"
    },

    "delete_organisation": {
        "entity": "organisation",
        "action": "deleted",
        "success_check": lambda result: isinstance(result, dict) and result.get("success") == True,
        "entity_id_extractor": lambda tool_call, result, user_id: tool_call.get("args", {}).get("organisation_slug", "unknown"),
        "description": "Organisation deleted by agent"
    },

    # Future: Opportunity tools
    # "create_opportunity": {...},
    # "update_opportunity": {...},
}


def extract_user_id_from_context() -> Optional[str]:
    """
    Extract user ID from current context.
    This is a placeholder - in practice, this would need access to the current user context.
    """
    # TODO: Implement proper user context extraction
    # This might need to be passed in from the agent state or request context
    return "current_user"


def extract_profile_id_from_result(result: str) -> Optional[str]:
    """
    Extract profile ID from tool result.
    Looks for patterns like "id=123" or "profile_id: 123"
    """
    import re

    # Look for id= pattern
    id_match = re.search(r'id=(\d+)', result)
    if id_match:
        return f"profile_{id_match.group(1)}"

    # Look for profile_id pattern
    profile_match = re.search(r'profile_id[:\s]+(\d+)', result)
    if profile_match:
        return f"profile_{profile_match.group(1)}"

    # Fallback
    return "unknown_profile"


def extract_profile_id_from_tool_call(tool_call: Dict[str, Any]) -> Optional[str]:
    """
    Extract profile ID from tool call arguments.
    """
    args = tool_call.get("args", tool_call.get("arguments", {}))
    if isinstance(args, dict):
        profile_id = args.get("profile_id")
        if profile_id:
            return f"profile_{profile_id}"

    return "unknown_profile"


def get_tool_event_config(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get event configuration for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Event configuration dict or None if tool doesn't emit events
    """
    return TOOL_EVENT_MAPPINGS.get(tool_name)


def create_thread_ui_event(action: str, thread_id: str, thread_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create a UI event for thread operations (creation, updates, title generation).

    Args:
        action: The action performed ("created", "updated", "title_updated")
        thread_id: The thread ID
        thread_data: Optional additional thread data

    Returns:
        UI event dict ready for writer
    """
    event_data = {
        "type": "ui",
        "entity": "thread",
        "entity_id": thread_id,
        "action": action,
        "description": f"Thread {action}"
    }

    # Add thread-specific data
    if thread_data:
        if action == "created" and "subject" in thread_data:
            event_data["subject"] = thread_data["subject"]
        elif action == "updated" and "message_count" in thread_data:
            event_data["message_count"] = thread_data["message_count"]
        elif action == "title_updated" and "subject" in thread_data:
            event_data["subject"] = thread_data["subject"]

    return event_data


def create_ui_event(tool_name: str, tool_call: Dict[str, Any], result: Any, user_id: str) -> Dict[str, Any]:
    """
    Create a UI event for a successful tool execution.

    Args:
        tool_name: Name of the tool
        tool_call: The original tool call dict
        result: The tool result
        user_id: Current user ID for context

    Returns:
        UI event dict ready for writer
    """
    config = get_tool_event_config(tool_name)
    if not config:
        raise ValueError(f"No event config for tool: {tool_name}")

    # Extract entity ID
    entity_id_extractor = config.get("entity_id_extractor")
    entity_id = "unknown"
    if entity_id_extractor and callable(entity_id_extractor):
        try:
            entity_id = entity_id_extractor(tool_call, result, user_id) or "unknown"
        except Exception as e:
            logger.warning(f"Failed to extract entity ID for {tool_name}: {e}")
            entity_id = "unknown"

    # Determine action based on tool configuration
    action = config["action"]
    target = None

    # Check if this tool should always navigate to a specific page
    always_navigate = config.get("always_navigate")
    if always_navigate:
        action = "navigate"
        target = always_navigate

    event_data = {
        "type": "ui",
        "entity": config["entity"],
        "entity_id": entity_id,
        "action": action,
        "tool": tool_name,
        "description": config.get("description", f"{tool_name} executed")
    }

    # Add target for navigation events
    if target:
        event_data["target"] = target

    # No need to parse changed fields - TanStack handles comparison

    return event_data
