"""
Utilities for user focus and session management in TalentCo.
"""

from django.contrib.auth.models import Group
from django.contrib import messages
from django.utils import timezone


async def get_available_foci_for_user(user):
    """
    Get list of available focus options for a user based on their groups.

    Returns:
        List of available focus strings: ['candidate', 'employer', 'admin']
    """
    from asgiref.sync import sync_to_async

    foci = []

    # Everyone can be a candidate (default - cannot be removed for UX reasons)
    foci.append('candidate')

    # Check for employer access
    if await sync_to_async(lambda: user.groups.filter(name='employer').exists())():
        foci.append('employer')

    # Check for recruiter access
    if await sync_to_async(lambda: user.groups.filter(name='recruiter').exists())():
        foci.append('recruiter')

    # Check for admin access
    if await sync_to_async(lambda: user.groups.filter(name='administrator').exists())():
        foci.append('admin')

    return foci


async def negotiate_user_focus(request, requested_focus=None):
    """
    Determine and set the user's current focus based on:
    1. Explicit request (form submission, API call)
    2. Session preference
    3. Group permissions
    4. Default fallback (candidate)

    Args:
        request: Django request object
        requested_focus: Optional focus to set ('candidate', 'employer', 'admin')

    Returns:
        tuple: (current_focus, error_message)
               error_message is None if successful
    """
    from asgiref.sync import sync_to_async

    # Try to get user from JWT token first (like agent API does)
    from yeshuman.api import get_user_from_token
    user = await get_user_from_token(request)

    # Fallback to request.user if JWT parsing fails
    if not user or user.is_anonymous:
        user = request.user

    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🎯 negotiate_user_focus called with user: {user}, type: {type(user)}")
    logger.info(f"🎯 user.is_authenticated: {getattr(user, 'is_authenticated', 'NO ATTR')}")
    logger.info(f"🎯 user.is_anonymous: {getattr(user, 'is_anonymous', 'NO ATTR')}")
    logger.info(f"🎯 hasattr is_authenticated: {hasattr(user, 'is_authenticated')}")

    # Must be authenticated - check both Django auth and manual user setting
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        # Also check if user is set manually (for API endpoints)
        if not user or getattr(user, 'is_anonymous', True):
            logger.error("🎯 User authentication check failed")
            return 'candidate', 'User must be authenticated'

    # Get available foci based on groups
    available_foci = await get_available_foci_for_user(user)

    # Handle explicit focus request
    if requested_focus:
        if requested_focus not in available_foci:
            return 'candidate', f'Focus "{requested_focus}" not available for this user'

        # Set the focus in session - use lambda for async-safe session access
        await sync_to_async(lambda: request.session.__setitem__('user_focus', requested_focus))()
        await sync_to_async(lambda: request.session.__setitem__('focus_timestamp', timezone.now().isoformat()))()
        await sync_to_async(lambda: request.session.__setitem__('focus_confirmed', True))()

        return requested_focus, None

    # Check session preference - use lambda for async-safe session access
    session_focus = await sync_to_async(lambda: request.session.get('user_focus'))()
    if session_focus and session_focus in available_foci:
        return session_focus, None

    # Default based on permissions (prefer candidate)
    if 'admin' in available_foci:
        default_focus = 'admin'
    else:
        default_focus = 'candidate'

    # Set default in session if not already set - use lambda for async-safe session access
    if not session_focus:
        await sync_to_async(lambda: request.session.__setitem__('user_focus', default_focus))()
        await sync_to_async(lambda: request.session.__setitem__('focus_timestamp', timezone.now().isoformat()))()
        await sync_to_async(lambda: request.session.__setitem__('focus_confirmed', False))()  # Default, not user-chosen

    return default_focus, None


async def get_selectable_groups_for_user(user):
    """
    Get all selectable groups for a user with their current assignment status.

    For testing purposes, all groups are selectable.
    Later this can be restricted based on subscriptions, verification, etc.

    Returns:
        List of dicts with group info: [
            {
                'name': 'candidate',
                'display_name': 'Job Seeker',
                'is_assigned': True,
                'can_focus': True
            },
            ...
        ]
    """
    from django.contrib.auth.models import Group
    from django.conf import settings
    from asgiref.sync import sync_to_async

    # Get all available groups
    all_groups = await sync_to_async(lambda: list(Group.objects.all()))()

    # Get user's current groups
    user_groups = set(await sync_to_async(lambda: list(user.groups.values_list('name', flat=True)))())

    # Get client-specific group names
    client_config = getattr(settings, 'CLIENT_GROUP_NAMES', {}).get(settings.CLIENT_CONFIG, {})
    default_names = getattr(settings, 'GROUP_PUBLIC_NAMES', {})

    result = []
    for group in all_groups:
        # Get display name (client-specific or default)
        display_name = client_config.get(group.name, default_names.get(group.name, group.name))

        # For testing: all groups are selectable
        # Everyone can be candidate (default group behavior)
        is_assigned = group.name in user_groups

        # Determine if this group can be used as focus
        # Map group names to focus names
        focus_mapping = {
            'candidate': 'candidate',
            'employer': 'employer',
            'recruiter': 'recruiter',
            'administrator': 'admin'
        }
        can_focus = group.name in focus_mapping

        result.append({
            'name': group.name,
            'display_name': display_name,
            'is_assigned': is_assigned,
            'can_focus': can_focus
        })

    # Sort to match focus menu order: candidate, employer, recruiter, administrator
    focus_order = ['candidate', 'employer', 'recruiter', 'administrator']
    def sort_key(group):
        try:
            return focus_order.index(group['name'])
        except ValueError:
            return len(focus_order)  # Put unknown groups at the end

    result.sort(key=sort_key)
    return result


async def update_user_groups(user, group_updates):
    """
    Update user's group memberships.

    Args:
        user: User instance
        group_updates: Dict of {group_name: should_assign}

    Returns:
        Dict with success status and details
    """
    from django.contrib.auth.models import Group
    from asgiref.sync import sync_to_async
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Get all groups for validation
        all_groups = {g.name: g for g in await sync_to_async(lambda: list(Group.objects.all()))()}

        # Track changes
        groups_added = []
        groups_removed = []

        # Process each update
        for group_name, should_assign in group_updates.items():
            if group_name not in all_groups:
                return {
                    'success': False,
                    'error': f'Group "{group_name}" does not exist'
                }

            group = all_groups[group_name]

            # Prevent removing the candidate group (required for all users)
            if group_name == 'candidate' and not should_assign:
                logger.info(f"Prevented removal of required candidate group for user {user.username}")
                continue

            if should_assign:
                # Add user to group
                await sync_to_async(user.groups.add)(group)
                groups_added.append(group_name)
                logger.info(f"Added user {user.username} to group {group_name}")
            else:
                # Remove user from group
                await sync_to_async(user.groups.remove)(group)
                groups_removed.append(group_name)
                logger.info(f"Removed user {user.username} from group {group_name}")

        # Clear focus-related session data since groups changed
        # This will force re-negotiation of focus on next request
        # We can't directly access request.session here, but the frontend
        # should invalidate focus queries after group updates

        message_parts = []
        if groups_added:
            message_parts.append(f"Added to: {', '.join(groups_added)}")
        if groups_removed:
            message_parts.append(f"Removed from: {', '.join(groups_removed)}")

        return {
            'success': True,
            'message': '; '.join(message_parts) if message_parts else 'No changes made',
            'groups_updated': {
                'added': groups_added,
                'removed': groups_removed
            }
        }

    except Exception as e:
        logger.error(f"Error updating groups for user {user.username}: {e}")
        return {
            'success': False,
            'error': f'Failed to update groups: {str(e)}'
        }


async def get_user_focus_context(request):
    """
    Get context dictionary with focus information.

    Returns:
        dict: Context with focus info
    """
    from asgiref.sync import sync_to_async

    focus, error = await negotiate_user_focus(request)
    available_foci = await get_available_foci_for_user(request.user)

    # Use lambda for async-safe session access
    focus_timestamp = await sync_to_async(lambda: request.session.get('focus_timestamp'))()
    focus_confirmed = await sync_to_async(lambda: request.session.get('focus_confirmed', False))()

    return {
        'current_focus': focus,
        'available_foci': available_foci,
        'focus_error': error,
        'can_switch_to_employer': 'employer' in available_foci,
        'can_switch_to_admin': 'admin' in available_foci,
        'focus_timestamp': focus_timestamp,
        'focus_confirmed': focus_confirmed,
    }
