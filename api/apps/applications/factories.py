import factory
import uuid
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from apps.organisations.models import Organisation
from apps.profiles.models import Profile
from apps.opportunities.models import Opportunity
from apps.evaluations.models import Evaluation
from apps.applications.models import (
    StageTemplate,
    Application,
    ApplicationStageInstance,
    ApplicationEvent,
    OpportunityQuestion,
    ApplicationAnswer,
    Interview,
)

User = get_user_model()


class OrganisationFactory(DjangoModelFactory):
    class Meta:
        model = Organisation

    name = factory.Sequence(lambda n: f"Test Organisation {n}")


class ProfileFactory(DjangoModelFactory):
    class Meta:
        model = Profile

    first_name = "Test"
    last_name = factory.Sequence(lambda n: f"User {n}")
    email = factory.Sequence(lambda n: f"test{n}@example.com")


class OpportunityFactory(DjangoModelFactory):
    class Meta:
        model = Opportunity

    title = factory.Sequence(lambda n: f"Software Engineer Position {n}")
    description = "A test opportunity"
    organisation = factory.SubFactory(OrganisationFactory)


class StageTemplateFactory(DjangoModelFactory):
    class Meta:
        model = StageTemplate

    name = factory.Sequence(lambda n: f"Stage {n}")
    slug = factory.Sequence(lambda n: f"stage_{n}")
    order = factory.Sequence(lambda n: n * 10)
    is_terminal = False


class ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = Application

    profile = factory.SubFactory(ProfileFactory)
    opportunity = factory.SubFactory(OpportunityFactory)
    organisation = factory.LazyAttribute(lambda obj: obj.opportunity.organisation)
    status = "applied"
    source = "direct"


class ApplicationStageInstanceFactory(DjangoModelFactory):
    class Meta:
        model = ApplicationStageInstance

    application = factory.SubFactory(ApplicationFactory)
    stage_template = factory.SubFactory(StageTemplateFactory)


class ApplicationEventFactory(DjangoModelFactory):
    class Meta:
        model = ApplicationEvent

    application = factory.SubFactory(ApplicationFactory)
    event_type = "applied"
    metadata = {}


class OpportunityQuestionFactory(DjangoModelFactory):
    class Meta:
        model = OpportunityQuestion

    opportunity = factory.SubFactory(OpportunityFactory)
    question_text = factory.Sequence(lambda n: f"Why do you want this job? {n}")
    question_type = "text"
    is_required = False
    order = factory.Sequence(lambda n: n)


class ApplicationAnswerFactory(DjangoModelFactory):
    class Meta:
        model = ApplicationAnswer

    application = factory.SubFactory(ApplicationFactory)
    question = factory.SubFactory(OpportunityQuestionFactory)
    answer_text = "Because I'm passionate about the work"
    answer_options = []
    is_disqualifying = False


class InterviewFactory(DjangoModelFactory):
    class Meta:
        model = Interview

    application = factory.SubFactory(ApplicationFactory)
    round_name = "Technical Interview"
    scheduled_start = factory.Faker("date_time_this_year")
    scheduled_end = factory.Faker("date_time_this_year")
    location_type = "virtual"
    location_details = "Zoom Meeting"
    outcome = "pending"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.Sequence(lambda n: f"testuser{n}@example.com")
    first_name = "Test"
    last_name = factory.Sequence(lambda n: f"User {n}")


class EvaluationFactory(DjangoModelFactory):
    class Meta:
        model = Evaluation

    opportunity = factory.SubFactory(OpportunityFactory)
    profile = factory.SubFactory(ProfileFactory)
    final_score = 85.5
    rank_in_set = 1
    component_scores = {"technical": 90, "cultural": 80}
    was_llm_judged = True
    llm_reasoning = "Good fit for the team"
