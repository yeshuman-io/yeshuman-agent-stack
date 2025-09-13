"""
Factory Boy factories for organisations app.
Used for testing and development data seeding.
"""

from factory.django import DjangoModelFactory
from factory import Faker, Sequence
from apps.organisations.models import Organisation


class OrganisationFactory(DjangoModelFactory):
    """Factory for creating Organisation instances."""

    class Meta:
        model = Organisation

    name = Sequence(lambda n: f"Test Organisation {n}")