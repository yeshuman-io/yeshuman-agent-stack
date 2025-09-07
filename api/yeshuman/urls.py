"""
URL configuration for yeshuman project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, re_path
from django.http import JsonResponse
from .api import api
from mcp.api import mcp_api
from a2a.api import a2a_api
from agent.api import agent_api

def simple_health_check(request):
    """Simple health check for Railway."""
    return JsonResponse({"status": "healthy", "service": "yeshuman-api"})

def fast_health_check(request):
    """Ultra-fast health check for Railway cold start detection."""
    return JsonResponse({"status": "ok", "timestamp": __import__('time').time()})

def oauth_discovery_no_auth(request):
    """OAuth discovery endpoint indicating no authentication required."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"OAuth discovery accessed by {request.META.get('REMOTE_ADDR')} - {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    return JsonResponse({
        "issuer": request.build_absolute_uri("/"),
        "service_documentation": "No authentication required for this MCP server"
    })

def mcp_oauth_discovery_no_auth(request):
    """MCP-specific OAuth discovery endpoint indicating no authentication required."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"MCP OAuth discovery accessed by {request.META.get('REMOTE_ADDR')} - {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    return JsonResponse({
        "issuer": request.build_absolute_uri("/"),
        "service_documentation": "MCP server - no authentication required"
    })

urlpatterns = [
    # Fast health check (must come first - ultra-fast response for Railway cold start detection)
    re_path(r'^ping$', fast_health_check),  # /ping - ultra-fast response

    # OAuth discovery endpoints (must come first)
    re_path(r'^\.well-known/oauth-authorization-server/?$', oauth_discovery_no_auth),
    re_path(r'^\.well-known/oauth-authorization-server/mcp/?$', mcp_oauth_discovery_no_auth),

    # API endpoints - flexible (accept both trailing slash and no trailing slash)
    re_path(r'^api/?', api.urls),          # /api, /api/, /api/subpath, etc.
    re_path(r'^mcp/?', mcp_api.urls),      # /mcp, /mcp/, /mcp/tools, /mcp/sse, etc.
    re_path(r'^a2a/?', a2a_api.urls),      # /a2a, /a2a/, /a2a/subpath, etc.
    re_path(r'^agent/?', agent_api.urls),  # /agent, /agent/, /agent/subpath, etc.
    re_path(r'^auth/?', include('django.contrib.auth.urls')),  # /auth, /auth/, /auth/subpath, etc.

    # Simple health check for Railway (bypasses potential URL routing issues)
    re_path(r'^health$', simple_health_check),
]
