"""
Tool services for the agent.

Handles tool selection and configuration based on user context.
"""

import logging
from typing import List, Any, Dict
from tools.compositions import get_tools_for_context, get_tools_for_user, get_tools_for_focus

logger = logging.getLogger('agent')


async def get_tools_for_request(user=None, focus=None, protocol: str = "graph") -> List[Any]:
    """
    Get appropriate tools for a request based on user and focus context.

    Args:
        user: Django User object
        focus: User focus string
        protocol: Protocol type ("graph", "mcp", "a2a")

    Returns:
        List of tool objects
    """
    if user and focus:
        logger.info(f"🔧 Loading tools for focus: user={user.username}, focus={focus}, protocol={protocol}")
        tools = await get_tools_for_focus(user, focus, protocol)
        logger.info(f"✅ Retrieved {len(tools)} tools for focus-based selection: {[t.name for t in tools]}")
    elif user:
        logger.info(f"👤 Loading tools for user groups: user={user.username}, protocol={protocol}")
        tools = await get_tools_for_user(user, protocol)
        logger.info(f"✅ Retrieved {len(tools)} tools for user-based selection: {[t.name for t in tools]}")
    else:
        logger.info(f"🏛️ Loading tools for legacy context: protocol={protocol}")
        tools = get_tools_for_context('talentco', 'admin', protocol)  # Default fallback
        logger.info(f"✅ Retrieved {len(tools)} tools for legacy context selection: {[t.name for t in tools]}")

    if not tools:
        logger.warning("No tools available for this context - agent will not be able to call any tools!")

    return tools


def inject_user_id_into_calls(tool_calls: List[Dict[str, Any]], user_id: str) -> None:
    """
    Inject user_id into tool call arguments where needed.

    Args:
        tool_calls: List of tool call dicts
        user_id: User identifier to inject
    """
    if not user_id:
        return

    for tc in tool_calls:
        tool_name = tc.get("name", "unknown")
        if tool_name in ["update_user_profile", "manage_user_profile"]:
            # Inject user_id into tool arguments
            args = tc.get("args", tc.get("arguments", {}))
            if not args.get("user_id"):
                args["user_id"] = int(user_id) if isinstance(user_id, str) else user_id
                tc["args"] = args
                logger.info(f"🔧 Injected user_id {user_id} into {tool_name} call")
