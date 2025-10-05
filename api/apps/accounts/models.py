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

    # Organisation management for employers (PoC: future multi-org support)
    managed_organisations = models.ManyToManyField(
        'organisations.Organisation',
        related_name='managers',
        blank=True,
        help_text="Organisations this user can manage"
    )

    def __str__(self):
        return self.email or self.username
