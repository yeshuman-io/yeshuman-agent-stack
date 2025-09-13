import pytest
import asyncio
from django.utils import timezone
from unittest.mock import patch
import pytest_asyncio

from apps.applications.services import ApplicationService, CreateApplicationResult
from apps.applications.models import (
    StageTemplate,
    Application,
    ApplicationStageInstance,
    ApplicationEvent,
    OpportunityQuestion,
    ApplicationAnswer,
    Interview,
)


class TestApplicationServiceStageManagement:
    """Test stage management methods in ApplicationService."""

    def test_seed_default_stages_creates_expected_stages(self):
        """Test that seed_default_stages creates all expected stages."""
        service = ApplicationService()
        stages = service.seed_default_stages()

        assert len(stages) == 7

        # Check that all expected stages are created
        stage_names = [stage.name for stage in stages]
        expected_names = ["Applied", "In Review", "Interview", "Offer", "Hired", "Rejected", "Withdrawn"]
        assert set(stage_names) == set(expected_names)

        # Check slugs
        stage_slugs = {stage.slug: stage for stage in stages}
        assert "applied" in stage_slugs
        assert "in_review" in stage_slugs
        assert "interview" in stage_slugs
        assert "offer" in stage_slugs
        assert "hired" in stage_slugs
        assert "rejected" in stage_slugs
        assert "withdrawn" in stage_slugs

    def test_seed_default_stages_updates_existing(self):
        """Test that seed_default_stages updates existing stages."""
        # Create a stage with different values
        StageTemplate.objects.create(
            slug="applied",
            name="Old Name",
            order=999,
            is_terminal=True
        )

        service = ApplicationService()
        stages = service.seed_default_stages()

        # Find the applied stage
        applied_stage = next(stage for stage in stages if stage.slug == "applied")
        assert applied_stage.name == "Applied"  # Should be updated
        assert applied_stage.order == 0  # Should be updated
        assert applied_stage.is_terminal is False  # Should be updated

    def test_seed_default_stages_idempotent(self):
        """Test that seed_default_stages is idempotent."""
        service = ApplicationService()
        stages1 = service.seed_default_stages()
        stages2 = service.seed_default_stages()

        assert len(stages1) == len(stages2)

        # Check that stages have same attributes
        for stage1, stage2 in zip(stages1, stages2):
            assert stage1.name == stage2.name
            assert stage1.slug == stage2.slug
            assert stage1.order == stage2.order
            assert stage1.is_terminal == stage2.is_terminal

    def test_list_stages_orders_correctly(self):
        """Test that list_stages returns stages in correct order."""
        service = ApplicationService()

        # Create stages with specific orders
        StageTemplate.objects.create(name="Third", slug="third", order=30)
        StageTemplate.objects.create(name="First", slug="first", order=10)
        StageTemplate.objects.create(name="Second", slug="second", order=20)

        stages = service.list_stages()
        assert len(stages) == 3
        assert stages[0].order == 10
        assert stages[1].order == 20
        assert stages[2].order == 30

    def test_upsert_stage_template_by_slug(self):
        """Test upserting stage template by slug."""
        service = ApplicationService()

        # Create new stage
        stage = service.upsert_stage_template({
            "slug": "test_stage",
            "name": "Test Stage",
            "order": 50,
            "is_terminal": False
        })

        assert stage.slug == "test_stage"
        assert stage.name == "Test Stage"
        assert stage.order == 50
        assert stage.is_terminal is False

        # Update existing stage
        updated_stage = service.upsert_stage_template({
            "slug": "test_stage",
            "name": "Updated Test Stage",
            "order": 60,
            "is_terminal": True
        })

        assert updated_stage.id == stage.id
        assert updated_stage.name == "Updated Test Stage"
        assert updated_stage.order == 60
        assert updated_stage.is_terminal is True

    def test_upsert_stage_template_by_id(self):
        """Test upserting stage template by ID."""
        service = ApplicationService()

        # Create initial stage
        stage = StageTemplate.objects.create(
            slug="test_stage",
            name="Test Stage",
            order=50
        )

        # Update by ID
        updated_stage = service.upsert_stage_template({
            "id": str(stage.id),
            "name": "Updated Name",
            "order": 75
        })

        assert updated_stage.id == stage.id
        assert updated_stage.name == "Updated Name"
        assert updated_stage.order == 75
        assert updated_stage.slug == "test_stage"  # Unchanged

    def test_upsert_stage_template_missing_identifier(self):
        """Test upserting stage template without slug or id raises error."""
        service = ApplicationService()

        with pytest.raises(ValueError, match="Provide either 'id' or 'slug'"):
            service.upsert_stage_template({
                "name": "Test Stage"
            })

    def test_delete_stage_template_by_slug(self):
        """Test deleting stage template by slug."""
        service = ApplicationService()

        StageTemplate.objects.create(slug="test_stage", name="Test Stage")

        deleted_count = service.delete_stage_template("test_stage")
        assert deleted_count == 1
        assert not StageTemplate.objects.filter(slug="test_stage").exists()

    def test_delete_stage_template_by_uuid(self):
        """Test deleting stage template by UUID."""
        service = ApplicationService()

        stage = StageTemplate.objects.create(slug="test_stage", name="Test Stage")

        deleted_count = service.delete_stage_template(str(stage.id))
        assert deleted_count == 1
        assert not StageTemplate.objects.filter(id=stage.id).exists()

    def test_delete_stage_template_nonexistent(self):
        """Test deleting nonexistent stage template."""
        service = ApplicationService()

        deleted_count = service.delete_stage_template("nonexistent")
        assert deleted_count == 0


class TestApplicationServiceApplicationCreation:
    """Test application creation methods in ApplicationService."""

    @pytest.mark.asyncio
    async def test_create_application_success(self, profile, opportunity):
        """Test successful application creation."""
        service = ApplicationService()

        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id)
        )

        assert result.created is True
        assert result.application.profile == profile
        assert result.application.opportunity == opportunity
        assert result.application.organisation == opportunity.organisation
        assert result.application.status == "applied"
        assert result.application.source == "direct"

        # Check that application was saved
        from asgiref.sync import sync_to_async
        exists_check = await sync_to_async(lambda: Application.objects.filter(id=result.application.id).exists())()
        assert exists_check

    @pytest.mark.asyncio
    async def test_create_application_prevents_duplicate(self, profile, opportunity):
        """Test that duplicate applications are prevented."""
        service = ApplicationService()

        # Create first application
        result1 = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id)
        )
        assert result1.created is True

        # Try to create duplicate
        result2 = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id)
        )
        assert result2.created is False
        assert result2.application == result1.application

    @pytest.mark.asyncio
    async def test_create_application_with_source(self, profile, opportunity):
        """Test creating application with custom source."""
        service = ApplicationService()

        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id),
            source="referral"
        )

        assert result.application.source == "referral"

    @pytest.mark.asyncio
    async def test_create_application_creates_initial_stage(self, profile, opportunity):
        """Test that application creation creates initial stage instance."""
        # Ensure we have a default stage
        StageTemplate.objects.create(slug="applied", name="Applied", order=0)

        service = ApplicationService()

        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id)
        )

        # Check that stage instance was created
        stage_instance = ApplicationStageInstance.objects.filter(
            application=result.application
        ).first()

        assert stage_instance is not None
        assert stage_instance.stage_template.slug == "applied"
        assert result.application.current_stage_instance == stage_instance

    @pytest.mark.asyncio
    async def test_create_application_creates_event(self, profile, opportunity):
        """Test that application creation creates audit event."""
        service = ApplicationService()

        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id)
        )

        # Check that event was created
        event = ApplicationEvent.objects.filter(
            application=result.application,
            event_type="applied"
        ).first()

        assert event is not None
        assert event.metadata == {}

    @pytest.mark.asyncio
    async def test_create_application_with_answers(self, profile, opportunity):
        """Test creating application with screening answers."""
        service = ApplicationService()

        # Create a question for the opportunity
        question = OpportunityQuestion.objects.create(
            opportunity=opportunity,
            question_text="Why do you want this job?",
            question_type="text"
        )

        answers = [{
            "question_id": str(question.id),
            "answer_text": "Because I'm passionate"
        }]

        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id),
            answers=answers
        )

        # Check that answer was created
        answer = ApplicationAnswer.objects.filter(
            application=result.application,
            question=question
        ).first()

        assert answer is not None
        assert answer.answer_text == "Because I'm passionate"

    @pytest.mark.asyncio
    @patch('apps.applications.services.EvaluationService')
    async def test_create_application_with_evaluation(self, mock_eval_service, profile, opportunity):
        """Test that application creation snapshots evaluation."""
        # Mock the evaluation service
        mock_eval_set = mock_eval_service.return_value.create_candidate_evaluation_set.return_value
        mock_evaluation = mock_eval_set.evaluations.filter.return_value.first.return_value

        # Configure mock evaluation
        mock_evaluation.final_score = 85.5
        mock_evaluation.rank_in_set = 1
        mock_evaluation.component_scores = {"technical": 90, "cultural": 80}
        mock_evaluation.was_llm_judged = True
        mock_evaluation.llm_reasoning = "Good fit"

        service = ApplicationService()

        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id)
        )

        # Check that evaluation was called
        mock_eval_service.return_value.create_candidate_evaluation_set.assert_called_once_with(str(opportunity.id))

        # Check that evaluation snapshot was created
        assert result.application.evaluation == mock_evaluation
        assert result.application.evaluation_snapshot == {
            "final_score": 85.5,
            "rank_in_set": 1,
            "component_scores": {"technical": 90, "cultural": 80},
            "was_llm_judged": True,
            "llm_reasoning": "Good fit"
        }


class TestApplicationServiceStageChanges:
    """Test stage change methods in ApplicationService."""

    @pytest.mark.asyncio
    async def test_change_stage_basic(self, application_with_stage, user):
        """Test basic stage change."""
        service = ApplicationService()

        # Create target stage
        new_stage = StageTemplate.objects.create(
            slug="in_review",
            name="In Review",
            order=10
        )

        result = await service.change_stage(
            application_id=str(application_with_stage.id),
            stage_slug="in_review",
            actor_id=user.id
        )

        assert result.status == "in_review"

        # Check that old stage was closed
        old_instance = application_with_stage.current_stage_instance
        old_instance.refresh_from_db()
        assert old_instance.exited_at is not None

        # Check that new stage instance was created
        new_instance = ApplicationStageInstance.objects.filter(
            application=application_with_stage,
            stage_template=new_stage
        ).first()

        assert new_instance is not None
        assert new_instance.entered_by == user
        assert application_with_stage.current_stage_instance == new_instance

    @pytest.mark.asyncio
    async def test_change_stage_with_slug_aliases(self, application_with_stage):
        """Test stage change with slug aliases."""
        service = ApplicationService()

        # Create target stages
        StageTemplate.objects.create(slug="in_review", name="In Review", order=10)
        StageTemplate.objects.create(slug="interview", name="Interview", order=20)

        # Test various aliases for in_review
        aliases = ["under-review", "under_review", "in-review", "screening", "review"]

        for alias in aliases:
            result = await service.change_stage(
                application_id=str(application_with_stage.id),
                stage_slug=alias
            )
            assert result.status == "in_review"

    @pytest.mark.asyncio
    async def test_change_stage_terminal_status_update(self, application_with_stage):
        """Test that terminal stages update application status correctly."""
        service = ApplicationService()

        # Create terminal stages
        hired_stage = StageTemplate.objects.create(
            slug="hired",
            name="Hired",
            order=100,
            is_terminal=True
        )
        rejected_stage = StageTemplate.objects.create(
            slug="rejected",
            name="Rejected",
            order=100,
            is_terminal=True
        )

        # Test hired status
        result = await service.change_stage(
            application_id=str(application_with_stage.id),
            stage_slug="hired"
        )
        assert result.status == "hired"

        # Test rejected status
        result = await service.change_stage(
            application_id=str(application_with_stage.id),
            stage_slug="rejected"
        )
        assert result.status == "rejected"

    @pytest.mark.asyncio
    async def test_change_stage_creates_event(self, application_with_stage):
        """Test that stage changes create audit events."""
        service = ApplicationService()

        StageTemplate.objects.create(slug="in_review", name="In Review", order=10)

        result = await service.change_stage(
            application_id=str(application_with_stage.id),
            stage_slug="in_review"
        )

        event = ApplicationEvent.objects.filter(
            application=application_with_stage,
            event_type="stage_changed"
        ).first()

        assert event is not None
        assert event.metadata == {"to_stage": "in_review"}


class TestApplicationServiceWithdrawals:
    """Test application withdrawal methods."""

    @pytest.mark.asyncio
    async def test_withdraw_application(self, application_with_stage):
        """Test withdrawing an application."""
        service = ApplicationService()

        result = await service.withdraw_application(
            application_id=str(application_with_stage.id),
            reason="Changed my mind"
        )

        assert result.status == "withdrawn"

        # Check that current stage was closed
        from asgiref.sync import sync_to_async
        stage_instance = application_with_stage.current_stage_instance
        await sync_to_async(stage_instance.refresh_from_db)()
        assert stage_instance.exited_at is not None

        # Check that event was created
        event_query = await sync_to_async(lambda: ApplicationEvent.objects.filter(
            application=application_with_stage,
            event_type="withdrawn"
        ).first())()

        assert event_query is not None
        assert event_query.metadata == {"reason": "Changed my mind"}

    @pytest.mark.asyncio
    async def test_record_decision_hired(self, application_with_stage):
        """Test recording a hire decision."""
        service = ApplicationService()

        result = await service.record_decision(
            application_id=str(application_with_stage.id),
            status="hired",
            reason_text="Great fit for the team"
        )

        assert result.status == "hired"

        # Check that event was created
        event = ApplicationEvent.objects.filter(
            application=application_with_stage,
            event_type="decision_made"
        ).first()

        assert event is not None
        assert event.metadata == {"status": "hired", "reason": "Great fit for the team"}

    @pytest.mark.asyncio
    async def test_record_decision_invalid_status(self, application_with_stage):
        """Test that invalid decision status raises error."""
        service = ApplicationService()

        with pytest.raises(AssertionError):
            await service.record_decision(
                application_id=str(application_with_stage.id),
                status="invalid_status"
            )
