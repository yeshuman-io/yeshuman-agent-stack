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

    # Everyone can be a candidate (default)
    foci.append('candidate')

    # Check for employer access
    if await sync_to_async(lambda: user.groups.filter(name='hiring').exists())():
        foci.append('employer')

    # Check for admin access
    if await sync_to_async(lambda: user.groups.filter(name='system_administration').exists())():
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

    # Default based on permissions (prefer employer for premium users)
    if 'admin' in available_foci:
        default_focus = 'admin'
    elif 'employer' in available_foci:
        default_focus = 'employer'
    else:
        default_focus = 'candidate'

    # Set default in session if not already set - use lambda for async-safe session access
    if not session_focus:
        await sync_to_async(lambda: request.session.__setitem__('user_focus', default_focus))()
        await sync_to_async(lambda: request.session.__setitem__('focus_timestamp', timezone.now().isoformat()))()
        await sync_to_async(lambda: request.session.__setitem__('focus_confirmed', False))()  # Default, not user-chosen

    return default_focus, None


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
