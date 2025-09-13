"""
App configuration for the accounts app.
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Custom app config to avoid label conflicts with django.contrib.auth"""
    name = 'apps.accounts'
    label = 'accounts'    
    verbose_name = 'Accounts'
