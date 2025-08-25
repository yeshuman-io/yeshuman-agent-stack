"""
Django app configuration for the agent app.
"""
from django.apps import AppConfig


class AgentConfig(AppConfig):
    """
    Configuration for the agent app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent'
    verbose_name = 'BookedAI Agent'
    
    def ready(self):
        """
        Perform initialization tasks when the app is ready.
        """
        # Import any signals or perform other initialization tasks here
        pass 