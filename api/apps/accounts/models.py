"""
Django models for accounts app.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Uses email as the primary identifier instead of username.
    """

    # Override email field to make it unique (required for USERNAME_FIELD)
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        error_messages={
            'unique': _("A user with that email address already exists."),
        },
    )

    # Use email as the username field for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # username becomes optional

    # Add custom fields if needed
    # For now, using Django's default User fields (username, email, password, etc.)

    def __str__(self):
        return self.email or self.username
