"""
Tool composition system using proper inheritance.
Each client/role combination has its own class, eliminating conditional logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from langchain_core.tools import BaseTool


class BaseToolComposition(ABC):
    """Abstract base class for all tool compositions."""

    def __init__(self, protocol: str = 'graph'):
        self.protocol = protocol
        self._tools = []
        self._metadata = {
            'protocol': protocol,
            'created_at': None,
            'version': '1.0'
        }
        self._compose_tools()
        self._apply_protocol_filters()

    @abstractmethod
    def _compose_tools(self):
        """Each concrete class implements its own tool composition."""
        pass

    def _apply_protocol_filters(self):
        """Apply protocol-specific filtering to all compositions."""
        if self.protocol == 'mcp':
            # Add discovery tools for external access
            from apps.applications.tools import APPLICATION_DISCOVERY_TOOLS
            from apps.opportunities.tools import OPPORTUNITY_DISCOVERY_TOOLS
            self._tools.extend(APPLICATION_DISCOVERY_TOOLS + OPPORTUNITY_DISCOVERY_TOOLS)

        # Graph and A2A get full access by default

    def get_tools(self) -> List[BaseTool]:
        """Get deduplicated tool list."""
        return self._deduplicate_tools(self._tools)

    def get_metadata(self) -> Dict[str, Any]:
        """Get composition metadata."""
        return self._metadata.copy()

    def _deduplicate_tools(self, tools: List[BaseTool]) -> List[BaseTool]:
        """Remove duplicate tools by name."""
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool.name not in seen:
                seen.add(tool.name)
                unique_tools.append(tool)
        return unique_tools


# ==========================================
# TALENTCO CLIENT COMPOSITIONS
# ==========================================

class TalentCoEmployerComposition(BaseToolComposition):
    """Employer role for TalentCo client."""

    def _compose_tools(self):
        from apps.opportunities.tools import OPPORTUNITY_MANAGEMENT_TOOLS
        from apps.evaluations.tools import EMPLOYER_EVALUATION_TOOLS
        from apps.applications.tools import (
            APPLICATION_CORE_TOOLS, APPLICATION_STAGE_TOOLS, APPLICATION_INTERVIEW_TOOLS
        )
        from tools.utilities import BASIC_TOOLS

        self._tools = (
            OPPORTUNITY_MANAGEMENT_TOOLS +
            EMPLOYER_EVALUATION_TOOLS +
            APPLICATION_CORE_TOOLS +
            APPLICATION_STAGE_TOOLS +
            APPLICATION_INTERVIEW_TOOLS +
            BASIC_TOOLS
        )

        self._metadata.update({
            'client': 'talentco',
            'role': 'employer',
            'description': 'Job posting, candidate evaluation, hiring management'
        })


class TalentCoCandidateComposition(BaseToolComposition):
    """Candidate role for TalentCo client."""

    def _compose_tools(self):
        # FOCUSED TESTING: Only UpdateUserProfileTool active
        from apps.profiles.tools import PROFILE_MANAGEMENT_TOOLS
        # from apps.profiles.tools import PROFILE_MANAGEMENT_TOOLS, PROFILE_DISCOVERY_TOOLS
        # from apps.evaluations.tools import CANDIDATE_EVALUATION_TOOLS
        # from apps.applications.tools import APPLICATION_DISCOVERY_TOOLS
        # from apps.opportunities.tools import OPPORTUNITY_DISCOVERY_TOOLS
        # from tools.utilities import BASIC_TOOLS

        # Extract only the UpdateUserProfileTool from PROFILE_MANAGEMENT_TOOLS
        update_user_profile_tool = None
        for tool in PROFILE_MANAGEMENT_TOOLS:
            if tool.name == "update_user_profile":
                update_user_profile_tool = tool
                break

        self._tools = [
            update_user_profile_tool,  # Only tool active for focused testing
            # PROFILE_MANAGEMENT_TOOLS +
            # PROFILE_DISCOVERY_TOOLS +
            # CANDIDATE_EVALUATION_TOOLS +
            # APPLICATION_DISCOVERY_TOOLS +
            # OPPORTUNITY_DISCOVERY_TOOLS +
            # BASIC_TOOLS
        ] if update_user_profile_tool else []

        self._metadata.update({
            'client': 'talentco',
            'role': 'candidate',
            'description': 'Profile management and job searching'
        })


class TalentCoAdminComposition(BaseToolComposition):
    """Admin role for TalentCo client."""

    def _compose_tools(self):
        # Admin gets all available tools
        from apps.opportunities.tools import OPPORTUNITY_MANAGEMENT_TOOLS
        from apps.profiles.tools import PROFILE_TOOLS
        from apps.evaluations.tools import EVALUATION_TOOLS
        from apps.applications.tools import (
            APPLICATION_CORE_TOOLS, APPLICATION_SCREENING_TOOLS,
            APPLICATION_STAGE_TOOLS, APPLICATION_INTERVIEW_TOOLS,
            APPLICATION_BULK_TOOLS, APPLICATION_DISCOVERY_TOOLS
        )
        from tools.utilities import BASIC_TOOLS

        self._tools = (
            OPPORTUNITY_MANAGEMENT_TOOLS +
            PROFILE_TOOLS +
            EVALUATION_TOOLS +
            APPLICATION_CORE_TOOLS +
            APPLICATION_SCREENING_TOOLS +
            APPLICATION_STAGE_TOOLS +
            APPLICATION_INTERVIEW_TOOLS +
            APPLICATION_BULK_TOOLS +
            APPLICATION_DISCOVERY_TOOLS +
            BASIC_TOOLS
        )

        self._metadata.update({
            'client': 'talentco',
            'role': 'admin',
            'description': 'Full system administration'
        })




# ==========================================
# USER GROUP MAPPING
# ==========================================

async def get_tools_for_user(user, protocol: str = 'graph') -> List[BaseTool]:
    """
    Get tools for authenticated user based on their Django Groups.
    Uses lowercase_underscore group naming convention.
    """
    import logging
    logger = logging.getLogger('tools.compositions')

    logger.info(f"👤 get_tools_for_user called: user={user.username}, protocol='{protocol}'")

    # Get user groups - wrap ORM call in sync_to_async for async context
    from asgiref.sync import sync_to_async
    user_groups = await sync_to_async(lambda: list(user.groups.all()))()

    logger.info(f"👥 User groups: {[g.name for g in user_groups]}")

    tools = []

    for group in user_groups:
        logger.debug(f"🔍 Processing group: {group.name}")

        # Direct Group name → Composition class mapping
        if group.name == 'hiring':
            logger.info(f"🏢 Adding employer tools for group '{group.name}'")
            composition = TalentCoEmployerComposition(protocol)
        elif group.name == 'job_seeking':
            logger.info(f"👤 Adding candidate tools for group '{group.name}'")
            composition = TalentCoCandidateComposition(protocol)
        elif group.name == 'system_administration':
            logger.info(f"👑 Adding admin tools for group '{group.name}'")
            composition = TalentCoAdminComposition(protocol)
        else:
            logger.debug(f"⏭️ Skipping unknown group: {group.name}")
            continue

        group_tools = composition.get_tools()
        logger.debug(f"📦 Group '{group.name}' provides {len(group_tools)} tools: {[t.name for t in group_tools]}")
        tools.extend(group_tools)

    # Deduplicate in case user is in multiple groups
    deduplicated_tools = _deduplicate_tools(tools)
    logger.info(f"✅ Final user tools: {len(deduplicated_tools)} tools - {[t.name for t in deduplicated_tools]}")
    return deduplicated_tools


def _deduplicate_tools(tools: List[BaseTool]) -> List[BaseTool]:
    """Remove duplicate tools by name."""
    seen = set()
    unique_tools = []
    for tool in tools:
        if tool.name not in seen:
            seen.add(tool.name)
            unique_tools.append(tool)
    return unique_tools


async def get_tools_for_focus(user, focus: str, protocol: str = 'graph') -> List[BaseTool]:
    """
    Get tools for a user based on their current focus.
    Focus overrides group-based logic for session-specific behavior.

    Args:
        user: Django User object
        focus: Current focus ('candidate', 'employer', 'admin')
        protocol: Protocol type ('graph', 'mcp', 'a2a')

    Returns:
        List of BaseTool objects appropriate for the focus
    """
    import logging
    logger = logging.getLogger('tools.compositions')

    logger.info(f"🎯 get_tools_for_focus called: user={user.username if user else 'None'}, focus='{focus}', protocol='{protocol}'")

    # Admin focus gets full access
    if focus == 'admin':
        logger.info(f"👑 Admin focus - returning all tools")
        tools = TalentCoAdminComposition(protocol).get_tools()
        logger.info(f"✅ Admin tools: {len(tools)} tools - {[t.name for t in tools]}")
        return tools

    # Employer focus
    elif focus == 'employer':
        logger.info(f"🏢 Employer focus requested")
        # Check permission
        from asgiref.sync import sync_to_async
        has_permission = await sync_to_async(lambda: user.groups.filter(name='hiring').exists())()

        if has_permission:
            logger.info(f"✅ User has hiring permission - returning employer tools")
            tools = TalentCoEmployerComposition(protocol).get_tools()
            logger.info(f"✅ Employer tools: {len(tools)} tools - {[t.name for t in tools]}")
            return tools
        else:
            logger.warning(f"🚫 User lacks hiring permission - falling back to candidate tools")
            tools = TalentCoCandidateComposition(protocol).get_tools()
            logger.info(f"✅ Fallback candidate tools: {len(tools)} tools - {[t.name for t in tools]}")
            return tools

    # Candidate focus (default)
    else:
        logger.info(f"👤 Candidate focus (default)")
        tools = TalentCoCandidateComposition(protocol).get_tools()
        logger.info(f"✅ Candidate tools: {len(tools)} tools - {[t.name for t in tools]}")
        return tools


# ==========================================
# LEGACY CONVENIENCE FUNCTIONS
# ==========================================

def get_tools_for_context(client: str = 'talentco', role: str = 'admin', protocol: str = 'graph') -> List[BaseTool]:
    """Get tools for a specific client/role/protocol context."""
    # Direct class instantiation - each client/role combination has its own class
    if client == 'talentco':
        if role == 'employer':
            return TalentCoEmployerComposition(protocol).get_tools()
        elif role == 'candidate':
            return TalentCoCandidateComposition(protocol).get_tools()
        elif role == 'admin':
            return TalentCoAdminComposition(protocol).get_tools()

    available = ['talentco/employer', 'talentco/candidate', 'talentco/admin']
    raise ValueError(f"No composition for {client}/{role}. Available: {available}")
