import pytest


@pytest.fixture
def organisation():
    from ..factories import OrganisationFactory
    return OrganisationFactory()




