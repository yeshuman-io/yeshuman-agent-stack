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
from django.contrib import admin
from django.urls import path, include, re_path
from .api import api
from mcp.api import mcp_api
from a2a.api import a2a_api
from agent.api import agent_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Includes /api/health endpoint
    # MCP endpoint - handle both /mcp and /mcp/ to avoid redirects
    re_path(r'^mcp/?', include(mcp_api.urls)),
    path('a2a/', a2a_api.urls),
    path('agent/', agent_api.urls),
    path('auth/', include('django.contrib.auth.urls')),
]
