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
from .api import api
from mcp.api import mcp_api
from a2a.api import a2a_api
from agent.api import agent_api

urlpatterns = [
    # API endpoints - flexible (accept both trailing slash and no trailing slash)
    re_path(r'^api/?', api.urls),          # /api, /api/, /api/subpath, etc.
    re_path(r'^mcp/?', mcp_api.urls),      # /mcp, /mcp/, /mcp/tools, /mcp/sse, etc.
    re_path(r'^a2a/?', a2a_api.urls),      # /a2a, /a2a/, /a2a/subpath, etc.
    re_path(r'^agent/?', agent_api.urls),  # /agent, /agent/, /agent/subpath, etc.
    re_path(r'^auth/?', include('django.contrib.auth.urls')),  # /auth, /auth/, /auth/subpath, etc.
]
