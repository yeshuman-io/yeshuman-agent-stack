from django.apps import AppConfig


class MemoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.memories'
    verbose_name = 'Mem0 Memory Storage'
    
    def ready(self):
        """Initialize any app-specific functionality when Django starts."""
        # Import signal handlers if we add them later
        # from . import signals
        pass 