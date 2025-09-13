import pytest
from django.test import TransactionTestCase


@pytest.fixture(autouse=True)
def clear_database():
    """Clear all database state before each test to ensure isolation."""
    from apps.organisations.models import Organisation
    from apps.profiles.models import Profile
    from apps.opportunities.models import Opportunity
    from apps.applications.models import (
        StageTemplate, Application, ApplicationStageInstance,
        ApplicationEvent, OpportunityQuestion, ApplicationAnswer, Interview
    )

    # Clear in reverse dependency order
    Interview.objects.all().delete()
    ApplicationAnswer.objects.all().delete()
    ApplicationEvent.objects.all().delete()
    ApplicationStageInstance.objects.all().delete()
    Application.objects.all().delete()
    OpportunityQuestion.objects.all().delete()
    Opportunity.objects.all().delete()
    Profile.objects.all().delete()
    Organisation.objects.all().delete()
    StageTemplate.objects.all().delete()


@pytest.fixture
def organisation():
    from ..factories import OrganisationFactory
    return OrganisationFactory()


@pytest.fixture
def profile(organisation):
    from ..factories import ProfileFactory
    return ProfileFactory()


@pytest.fixture
def opportunity(organisation):
    from ..factories import OpportunityFactory
    return OpportunityFactory()


@pytest.fixture
def stage_template():
    from ..factories import StageTemplateFactory
    return StageTemplateFactory()


@pytest.fixture
def application(profile, opportunity):
    from ..factories import ApplicationFactory
    return ApplicationFactory(profile=profile, opportunity=opportunity)


@pytest.fixture
def application_with_stage(application, stage_template):
    """Application with a current stage instance."""
    from ..factories import ApplicationStageInstanceFactory
    stage_instance = ApplicationStageInstanceFactory(
        application=application,
        stage_template=stage_template
    )
    application.current_stage_instance = stage_instance
    application.save()
    return application


@pytest.fixture
def application_event(application):
    from ..factories import ApplicationEventFactory
    return ApplicationEventFactory(application=application)


@pytest.fixture
def opportunity_question(opportunity):
    from ..factories import OpportunityQuestionFactory
    return OpportunityQuestionFactory(opportunity=opportunity)


@pytest.fixture
def application_answer(application, opportunity_question):
    from ..factories import ApplicationAnswerFactory
    return ApplicationAnswerFactory(
        application=application,
        question=opportunity_question
    )


@pytest.fixture
def interview(application):
    from ..factories import InterviewFactory
    return InterviewFactory(application=application)


@pytest.fixture
def user():
    from ..factories import UserFactory
    return UserFactory()


@pytest.fixture
def evaluation(opportunity, profile):
    from ..factories import EvaluationFactory
    return EvaluationFactory(opportunity=opportunity, profile=profile)


@pytest.fixture
def default_stages():
    """Create the default stage templates."""
    from apps.applications.services import ApplicationService
    service = ApplicationService()
    return service.seed_default_stages()
