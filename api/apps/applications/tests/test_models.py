import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.applications.models import (
    StageTemplate,
    Application,
    ApplicationStageInstance,
    ApplicationEvent,
    OpportunityQuestion,
    ApplicationAnswer,
    Interview,
)


class TestStageTemplate:
    """Test StageTemplate model."""

    def test_create_stage_template(self):
        """Test creating a basic stage template."""
        # Clear existing stages first
        StageTemplate.objects.all().delete()

        stage = StageTemplate.objects.create(
            name="Applied",
            slug="applied",
            order=0,
            is_terminal=False
        )

        assert stage.name == "Applied"
        assert stage.slug == "applied"
        assert stage.order == 0
        assert stage.is_terminal is False
        assert str(stage) == "Applied"

    def test_stage_template_ordering(self):
        """Test that stages are ordered by order field."""
        # Clear existing stages first
        StageTemplate.objects.all().delete()

        stage1 = StageTemplate.objects.create(name="First", slug="first", order=10)
        stage2 = StageTemplate.objects.create(name="Second", slug="second", order=5)
        stage3 = StageTemplate.objects.create(name="Third", slug="third", order=15)

        stages = list(StageTemplate.objects.all())
        assert stages[0] == stage2  # order=5
        assert stages[1] == stage1  # order=10
        assert stages[2] == stage3  # order=15

    def test_unique_slug_constraint(self):
        """Test that slug must be unique."""
        # Clear existing stages first
        StageTemplate.objects.all().delete()

        StageTemplate.objects.create(name="Applied", slug="applied", order=0)

        with pytest.raises(IntegrityError):
            StageTemplate.objects.create(name="Applied 2", slug="applied", order=1)

    def test_terminal_stage(self):
        """Test terminal stage functionality."""
        # Clear existing stages first
        StageTemplate.objects.all().delete()

        stage = StageTemplate.objects.create(
            name="Hired",
            slug="hired",
            order=100,
            is_terminal=True
        )

        assert stage.is_terminal is True


class TestApplication:
    """Test Application model."""

    def test_create_application(self, application):
        """Test creating a basic application."""
        assert application.status == "applied"
        assert application.source == "direct"
        assert application.evaluation_snapshot == {}
        assert application.applied_at is not None
        assert str(application) == f"{application.profile} → {application.opportunity} (applied)"

    def test_unique_profile_opportunity_constraint(self, profile, opportunity):
        """Test that profile-opportunity pair must be unique."""
        Application.objects.create(
            profile=profile,
            opportunity=opportunity,
            organisation=opportunity.organisation
        )

        with pytest.raises(IntegrityError):
            Application.objects.create(
                profile=profile,
                opportunity=opportunity,
                organisation=opportunity.organisation
            )

    def test_application_status_choices(self, application):
        """Test valid status choices."""
        valid_statuses = ["applied", "in_review", "interview", "offer", "hired", "rejected", "withdrawn"]

        for status in valid_statuses:
            application.status = status
            application.save()
            application.refresh_from_db()
            assert application.status == status

    def test_application_source_choices(self, application):
        """Test valid source choices."""
        valid_sources = ["direct", "referral", "internal", "import", "agency"]

        for source in valid_sources:
            application.source = source
            application.save()
            application.refresh_from_db()
            assert application.source == source

    def test_current_stage_instance_relationship(self, application, stage_template):
        """Test current stage instance relationship."""
        stage_instance = ApplicationStageInstance.objects.create(
            application=application,
            stage_template=stage_template
        )

        application.current_stage_instance = stage_instance
        application.save()

        application.refresh_from_db()
        assert application.current_stage_instance == stage_instance

    def test_application_indexes(self, application):
        """Test that indexes are created for performance."""
        # This is more of a documentation test - the indexes are defined in Meta
        # We can verify they're there by checking the Meta class
        meta = Application._meta
        indexes = [index.fields for index in meta.indexes]

        assert ["organisation", "status"] in indexes
        assert ["opportunity", "status"] in indexes


class TestApplicationStageInstance:
    """Test ApplicationStageInstance model."""

    def test_create_stage_instance(self, application, stage_template):
        """Test creating a stage instance."""
        instance = ApplicationStageInstance.objects.create(
            application=application,
            stage_template=stage_template
        )

        assert instance.application == application
        assert instance.stage_template == stage_template
        assert instance.entered_at is not None
        assert instance.exited_at is None
        assert str(instance) == f"{application} @ {stage_template.name}"

    def test_is_open_property(self, application, stage_template):
        """Test is_open property."""
        instance = ApplicationStageInstance.objects.create(
            application=application,
            stage_template=stage_template
        )

        assert instance.is_open is True

        instance.close()
        instance.refresh_from_db()
        assert instance.is_open is False

    def test_close_method(self, application, stage_template):
        """Test closing a stage instance."""
        instance = ApplicationStageInstance.objects.create(
            application=application,
            stage_template=stage_template
        )

        assert instance.exited_at is None

        instance.close()

        instance.refresh_from_db()
        assert instance.exited_at is not None


class TestApplicationEvent:
    """Test ApplicationEvent model."""

    def test_create_event(self, application):
        """Test creating an application event."""
        event = ApplicationEvent.objects.create(
            application=application,
            event_type="applied",
            metadata={"test": "data"}
        )

        assert event.application == application
        assert event.event_type == "applied"
        assert event.metadata == {"test": "data"}
        assert event.created_at is not None
        assert str(event) == f"{application}: applied"

    def test_event_ordering(self, application):
        """Test that events are ordered by created_at descending."""
        event1 = ApplicationEvent.objects.create(application=application, event_type="applied")
        event2 = ApplicationEvent.objects.create(application=application, event_type="stage_changed")

        events = list(ApplicationEvent.objects.all())
        assert events[0] == event2  # Most recent first
        assert events[1] == event1

    def test_event_types(self, application):
        """Test valid event types."""
        valid_types = ["applied", "stage_changed", "decision_made", "withdrawn", "note_added"]

        for event_type in valid_types:
            event = ApplicationEvent.objects.create(
                application=application,
                event_type=event_type
            )
            assert event.event_type == event_type


class TestOpportunityQuestion:
    """Test OpportunityQuestion model."""

    def test_create_question(self, opportunity):
        """Test creating a screening question."""
        # Clear existing questions first
        OpportunityQuestion.objects.all().delete()

        question = OpportunityQuestion.objects.create(
            opportunity=opportunity,
            question_text="Why do you want this job?",
            question_type="text",
            is_required=True,
            order=1,
            config={"max_length": 500}
        )

        assert question.opportunity == opportunity
        assert question.question_text == "Why do you want this job?"
        assert question.question_type == "text"
        assert question.is_required is True
        assert question.order == 1
        assert question.config == {"max_length": 500}
        # Check that string representation contains the expected parts
        str_repr = str(question)
        assert "Why do you want this job?" in str_repr
        assert str(opportunity) in str_repr

    def test_question_ordering(self, opportunity):
        """Test that questions are ordered by opportunity, order, id."""
        # Clear existing questions first
        OpportunityQuestion.objects.all().delete()

        q1 = OpportunityQuestion.objects.create(
            opportunity=opportunity,
            question_text="Question 1",
            question_type="text",
            order=2
        )
        q2 = OpportunityQuestion.objects.create(
            opportunity=opportunity,
            question_text="Question 2",
            question_type="text",
            order=1
        )

        questions = list(OpportunityQuestion.objects.filter(opportunity=opportunity))
        assert questions[0] == q2  # order=1
        assert questions[1] == q1  # order=2

    def test_question_types(self, opportunity):
        """Test valid question types."""
        valid_types = ["text", "boolean", "single_choice", "multi_choice", "number"]

        for q_type in valid_types:
            question = OpportunityQuestion.objects.create(
                opportunity=opportunity,
                question_text=f"Test {q_type}",
                question_type=q_type
            )
            assert question.question_type == q_type


class TestApplicationAnswer:
    """Test ApplicationAnswer model."""

    def test_create_answer(self, application, opportunity_question):
        """Test creating an application answer."""
        answer = ApplicationAnswer.objects.create(
            application=application,
            question=opportunity_question,
            answer_text="Because I'm passionate about the work",
            answer_options=["option1"],
            is_disqualifying=False
        )

        assert answer.application == application
        assert answer.question == opportunity_question
        assert answer.answer_text == "Because I'm passionate about the work"
        assert answer.answer_options == ["option1"]
        assert answer.is_disqualifying is False
        assert str(answer) == f"Answer {opportunity_question.id} for {application.id}"

    def test_unique_application_question_constraint(self, application, opportunity_question):
        """Test that application-question pair must be unique."""
        ApplicationAnswer.objects.create(
            application=application,
            question=opportunity_question
        )

        with pytest.raises(IntegrityError):
            ApplicationAnswer.objects.create(
                application=application,
                question=opportunity_question
            )


class TestInterview:
    """Test Interview model."""

    def test_create_interview(self, application):
        """Test creating an interview."""
        start_time = timezone.now()
        end_time = start_time.replace(hour=start_time.hour + 1)

        interview = Interview.objects.create(
            application=application,
            round_name="Technical Interview",
            scheduled_start=start_time,
            scheduled_end=end_time,
            location_type="virtual",
            location_details="Zoom Meeting",
            outcome="pending"
        )

        assert interview.application == application
        assert interview.round_name == "Technical Interview"
        assert interview.scheduled_start == start_time
        assert interview.scheduled_end == end_time
        assert interview.location_type == "virtual"
        assert interview.location_details == "Zoom Meeting"
        assert interview.outcome == "pending"
        assert str(interview) == f"Interview for {application.id} - Technical Interview"

    def test_interview_location_types(self, application):
        """Test valid location types."""
        valid_types = ["virtual", "onsite"]

        for location_type in valid_types:
            interview = Interview.objects.create(
                application=application,
                round_name="Interview",
                scheduled_start=timezone.now(),
                scheduled_end=timezone.now().replace(hour=timezone.now().hour + 1),
                location_type=location_type
            )
            assert interview.location_type == location_type

    def test_interview_outcomes(self, application):
        """Test valid outcomes."""
        valid_outcomes = ["pending", "pass", "fail"]

        for outcome in valid_outcomes:
            interview = Interview.objects.create(
                application=application,
                round_name="Interview",
                scheduled_start=timezone.now(),
                scheduled_end=timezone.now().replace(hour=timezone.now().hour + 1),
                outcome=outcome
            )
            assert interview.outcome == outcome
