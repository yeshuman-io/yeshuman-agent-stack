"""
Factory Boy factories for profiles app.
Used for testing and development data seeding.
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker, Sequence
from apps.profiles.models import Profile


class ProfileFactory(DjangoModelFactory):
    """Factory for creating Profile instances."""

    class Meta:
        model = Profile

    first_name = Faker('first_name')
    last_name = Faker('last_name')
    email = Sequence(lambda n: f'test{n}@example.com')
