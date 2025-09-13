import pytest


@pytest.fixture
def profile():
    from ..factories import ProfileFactory
    return ProfileFactory()
