"""
Utilities for user focus and session management in TalentCo.
"""

from django.contrib.auth.models import Group
from django.contrib import messages
from django.utils import timezone


def get_available_foci_for_user(user):
    """
    Get list of available focus options for a user based on their groups.

    Returns:
        List of available focus strings: ['candidate', 'employer', 'admin']
    """
    foci = []

    # Everyone can be a candidate (default)
    foci.append('candidate')

    # Check for employer access
    if user.groups.filter(name='hiring').exists():
        foci.append('employer')

    # Check for admin access
    if user.groups.filter(name='system_administration').exists():
        foci.append('admin')

    return foci


def negotiate_user_focus(request, requested_focus=None):
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
    available_foci = get_available_foci_for_user(user)

    # Handle explicit focus request
    if requested_focus:
        if requested_focus not in available_foci:
            return 'candidate', f'Focus "{requested_focus}" not available for this user'

        # Set the focus in session
        request.session['user_focus'] = requested_focus
        request.session['focus_timestamp'] = timezone.now().isoformat()
        request.session['focus_confirmed'] = True

        return requested_focus, None

    # Check session preference
    session_focus = request.session.get('user_focus')
    if session_focus and session_focus in available_foci:
        return session_focus, None

    # Default based on permissions (prefer employer for premium users)
    if 'admin' in available_foci:
        default_focus = 'admin'
    elif 'employer' in available_foci:
        default_focus = 'employer'
    else:
        default_focus = 'candidate'

    # Set default in session if not already set
    if not session_focus:
        request.session['user_focus'] = default_focus
        request.session['focus_timestamp'] = timezone.now().isoformat()
        request.session['focus_confirmed'] = False  # Default, not user-chosen

    return default_focus, None


def set_user_focus(request, focus):
    """
    Convenience function to set user focus and handle errors.

    Args:
        request: Django request object
        focus: Focus to set ('candidate', 'employer', 'admin')

    Returns:
        bool: True if successful, False if error
    """
    current_focus, error = negotiate_user_focus(request, focus)

    if error:
        messages.error(request, error)
        return False
    else:
        messages.success(request, f'Switched to {focus} focus')
        return True


def get_user_focus_context(request):
    """
    Get context dictionary for templates with focus information.

    Returns:
        dict: Context with focus info for template rendering
    """
    focus, error = negotiate_user_focus(request)
    available_foci = get_available_foci_for_user(request.user)

    return {
        'current_focus': focus,
        'available_foci': available_foci,
        'focus_error': error,
        'can_switch_to_employer': 'employer' in available_foci,
        'can_switch_to_admin': 'admin' in available_foci,
        'focus_timestamp': request.session.get('focus_timestamp'),
        'focus_confirmed': request.session.get('focus_confirmed', False),
    }
