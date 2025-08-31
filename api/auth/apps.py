"""
App configuration for the auth app.
"""
from django.apps import AppConfig


class AuthConfig(AppConfig):
    """Custom app config to avoid label conflicts with django.contrib.auth"""
    name = 'auth'
    label = 'yeshuman_auth'  # Unique label to avoid conflicts
    verbose_name = 'YesHuman Authentication'
