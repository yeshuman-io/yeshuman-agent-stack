"""
Factory Boy factories for skills app.
Used for testing and development data seeding.
"""

from factory.django import DjangoModelFactory
from factory import Faker, Sequence
from apps.skills.models import Skill


class SkillFactory(DjangoModelFactory):
    """Factory for creating Skill instances."""

    class Meta:
        model = Skill

    name = Sequence(lambda n: f"Skill {n}")
