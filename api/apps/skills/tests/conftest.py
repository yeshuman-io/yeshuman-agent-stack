import pytest


@pytest.fixture
def skill():
    from ..factories import SkillFactory
    return SkillFactory()




