"""
Django models for accounts app.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Adds any custom fields specific to Yes Human here.
    """

    # Add custom fields if needed
    # For now, using Django's default User fields (username, email, password, etc.)

    def __str__(self):
        return self.username
