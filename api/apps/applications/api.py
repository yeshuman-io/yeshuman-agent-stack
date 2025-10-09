"""
API endpoints for applications app using Django Ninja.
"""

from ninja import Router
from typing import List, Optional
from datetime import datetime
from apps.applications.models import (
    Application,
    StageTemplate,
    ApplicationStageInstance,
    ApplicationEvent,
    OpportunityQuestion,
    ApplicationAnswer,
    Interview
)
from apps.applications.services import ApplicationService
from apps.applications.schemas import (
    # Application schemas
    ApplicationStageSchema,
    ApplicationSchema,
    ApplicationCreateSchema,
    ApplicationApplySchema,
    ApplicationInviteSchema,

    # Stage management schemas
    StageTemplateSchema,
    StageChangeSchema,

    # Application action schemas
    ApplicationActionSchema,
    DecisionSchema,

    # Event schemas
    ApplicationEventSchema,

    # Screening schemas
    OpportunityQuestionSchema,
    ApplicationAnswerSchema,
    ScreeningAnswersSchema,

    # Interview schemas
    InterviewSchema,
    InterviewCreateSchema,
)

# Create router for applications endpoints
applications_router = Router()


@applications_router.get("/", response=List[ApplicationSchema], tags=["Applications"])
async def list_applications(request):
    """List all applications."""
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_applications_sync():
        return list(Application.objects.all().prefetch_related(
            'profile', 'opportunity', 'organisation', 'current_stage_instance__stage_template'
        ))

    applications = await get_applications_sync()
    return [
        ApplicationSchema(
            id=str(app.id),
            profile_id=str(app.profile.id),
            opportunity_title=app.opportunity.title,
            organisation_name=app.organisation.name,
            status=app.status,
            source=app.source,
            applied_at=app.applied_at.isoformat(),
            current_stage=ApplicationStageSchema(
                id=str(app.current_stage_instance.id),
                stage_name=app.current_stage_instance.stage_template.name,
                entered_at=app.current_stage_instance.entered_at.isoformat(),
                is_open=app.current_stage_instance.is_open
            ) if app.current_stage_instance else None
        )
        for app in applications
    ]


@applications_router.post("/", response={200: ApplicationSchema, 404: dict, 400: dict}, tags=["Applications"])
async def create_application(request, payload: ApplicationCreateSchema):
    """Create a new application."""
    from asgiref.sync import sync_to_async
    from apps.profiles.models import Profile
    from apps.opportunities.models import Opportunity
    from apps.organisations.models import Organisation

    # Validate that profile, opportunity, and organisation exist
    @sync_to_async
    def validate_entities():
        try:
            Profile.objects.get(id=payload.profile_id)
            Opportunity.objects.get(id=payload.opportunity_id)
            Organisation.objects.get(id=payload.organisation_id)
            return None
        except Profile.DoesNotExist:
            return "Profile not found"
        except Opportunity.DoesNotExist:
            return "Opportunity not found"
        except Organisation.DoesNotExist:
            return "Organisation not found"

    error = await validate_entities()
    if error:
        return 404, {"error": error}

    # Create application using the service
    service = ApplicationService()
    try:
        result = await service.create_application(
            profile_id=payload.profile_id,
            opportunity_id=payload.opportunity_id,
            source=payload.source
        )
    except Exception as e:
        return 400, {"error": str(e)}

    application = result.application

    return 200, ApplicationSchema(
        id=str(application.id),
        profile_id=str(application.profile.id),
        opportunity_title=application.opportunity.title,
        organisation_name=application.organisation.name,
        status=application.status,
        source=application.source,
        applied_at=application.applied_at.isoformat(),
        current_stage=ApplicationStageSchema(
            id=str(application.current_stage_instance.id),
            stage_name=application.current_stage_instance.stage_template.name,
            entered_at=application.current_stage_instance.entered_at.isoformat(),
            is_open=application.current_stage_instance.is_open
        ) if application.current_stage_instance else None
    )


# -----------------------------
# Stage Management Endpoints
# -----------------------------

@applications_router.get("/stages/", response=List[StageTemplateSchema], tags=["Stages"])
async def list_stages(request):
    """List all available stage templates."""
    service = ApplicationService()
    stages = service.list_stages()
    return [
        StageTemplateSchema(
            id=str(stage.id),
            name=stage.name,
            slug=stage.slug,
            order=stage.order,
            is_terminal=stage.is_terminal
        )
        for stage in stages
    ]


@applications_router.post("/seed-stages/", response=List[StageTemplateSchema], tags=["Stages"])
async def seed_default_stages(request):
    """Seed default stage templates (admin only)."""
    service = ApplicationService()
    stages = service.seed_default_stages()
    return [
        StageTemplateSchema(
            id=str(stage.id),
            name=stage.name,
            slug=stage.slug,
            order=stage.order,
            is_terminal=stage.is_terminal
        )
        for stage in stages
    ]


# -----------------------------
# Application Actions Endpoints
# -----------------------------

@applications_router.post("/{application_id}/change-stage/", response={200: ApplicationSchema, 404: dict, 400: dict}, tags=["Applications"])
async def change_application_stage(request, application_id: str, payload: StageChangeSchema):
    """Change the stage of an application."""
    service = ApplicationService()
    try:
        application = service.change_stage(
            application_id=application_id,
            stage_slug=payload.stage_slug,
            actor_id=payload.actor_id
        )
        # Refresh from database to get updated current_stage_instance
        application.refresh_from_db()
    except Application.DoesNotExist:
        return 404, {"error": "Application not found"}
    except StageTemplate.DoesNotExist:
        return 400, {"error": "Invalid stage"}
    except Exception as e:
        return 400, {"error": str(e)}

    return 200, ApplicationSchema(
        id=str(application.id),
        profile_id=str(application.profile.id),
        opportunity_title=application.opportunity.title,
        organisation_name=application.organisation.name,
        status=application.status,
        source=application.source,
        applied_at=application.applied_at.isoformat(),
        current_stage=ApplicationStageSchema(
            id=str(application.current_stage_instance.id),
            stage_name=application.current_stage_instance.stage_template.name,
            entered_at=application.current_stage_instance.entered_at.isoformat(),
            is_open=application.current_stage_instance.is_open
        ) if application.current_stage_instance else None
    )


@applications_router.post("/{application_id}/withdraw/", response={200: ApplicationSchema, 404: dict, 400: dict}, tags=["Applications"])
async def withdraw_application(request, application_id: str, payload: ApplicationActionSchema):
    """Withdraw an application."""
    service = ApplicationService()
    try:
        application = service.withdraw_application(
            application_id=application_id,
            reason=payload.reason
        )
        # Refresh from database to get updated current_stage_instance
        application.refresh_from_db()
    except Application.DoesNotExist:
        return 404, {"error": "Application not found"}
    except Exception as e:
        return 400, {"error": str(e)}

    return 200, ApplicationSchema(
        id=str(application.id),
        profile_id=str(application.profile.id),
        opportunity_title=application.opportunity.title,
        organisation_name=application.organisation.name,
        status=application.status,
        source=application.source,
        applied_at=application.applied_at.isoformat(),
        current_stage=ApplicationStageSchema(
            id=str(application.current_stage_instance.id),
            stage_name=application.current_stage_instance.stage_template.name,
            entered_at=application.current_stage_instance.entered_at.isoformat(),
            is_open=application.current_stage_instance.is_open
        ) if application.current_stage_instance else None
    )


@applications_router.post("/{application_id}/decision/", response={200: ApplicationSchema, 404: dict, 400: dict}, tags=["Applications"])
async def record_decision(request, application_id: str, payload: DecisionSchema):
    """Record a decision on an application."""
    service = ApplicationService()
    try:
        application = service.record_decision(
            application_id=application_id,
            status=payload.status,
            reason_text=payload.reason
        )
        # Refresh from database to get updated current_stage_instance
        application.refresh_from_db()
    except Application.DoesNotExist:
        return 404, {"error": "Application not found"}
    except AssertionError:
        return 400, {"error": "Invalid decision status"}
    except Exception as e:
        return 400, {"error": str(e)}

    return 200, ApplicationSchema(
        id=str(application.id),
        profile_id=str(application.profile.id),
        opportunity_title=application.opportunity.title,
        organisation_name=application.organisation.name,
        status=application.status,
        source=application.source,
        applied_at=application.applied_at.isoformat(),
        current_stage=ApplicationStageSchema(
            id=str(application.current_stage_instance.id),
            stage_name=application.current_stage_instance.stage_template.name,
            entered_at=application.current_stage_instance.entered_at.isoformat(),
            is_open=application.current_stage_instance.is_open
        ) if application.current_stage_instance else None
    )


# -----------------------------
# Screening Endpoints
# -----------------------------

@applications_router.get("/{application_id}/questions/", response=List[OpportunityQuestionSchema], tags=["Screening"])
async def get_application_questions(request, application_id: str):
    """Get screening questions for an application."""
    try:
        application = Application.objects.select_related('opportunity').get(id=application_id)
    except Application.DoesNotExist:
        # Return empty list if application doesn't exist
        return []

    questions = application.opportunity.questions.all().order_by('order')
    return [
        OpportunityQuestionSchema(
            id=str(q.id),
            question_text=q.question_text,
            question_type=q.question_type,
            is_required=q.is_required,
            order=q.order,
            config=q.config or {}
        )
        for q in questions
    ]


@applications_router.post("/{application_id}/answers/", response={200: List[ApplicationAnswerSchema], 404: dict, 400: dict}, tags=["Screening"])
async def submit_screening_answers(request, application_id: str, payload: ScreeningAnswersSchema):
    """Submit screening answers for an application."""
    service = ApplicationService()
    try:
        answers = service.submit_answers(
            application_id=application_id,
            answers_payload=payload.answers
        )
    except Application.DoesNotExist:
        return 404, {"error": "Application not found"}
    except Exception as e:
        return 400, {"error": str(e)}

    return 200, [
        ApplicationAnswerSchema(
            id=str(answer.id),
            question_id=str(answer.question.id),
            answer_text=answer.answer_text,
            answer_options=answer.answer_options,
            is_disqualifying=answer.is_disqualifying
        )
        for answer in answers
    ]


@applications_router.get("/{application_id}/answers/", response=List[ApplicationAnswerSchema], tags=["Screening"])
async def get_application_answers(request, application_id: str):
    """Get screening answers for an application."""
    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        return []

    answers = application.answers.all().select_related('question')
    return [
        ApplicationAnswerSchema(
            id=str(answer.id),
            question_id=str(answer.question.id),
            answer_text=answer.answer_text,
            answer_options=answer.answer_options,
            is_disqualifying=answer.is_disqualifying
        )
        for answer in answers
    ]


# -----------------------------
# Interview Endpoints
# -----------------------------

@applications_router.post("/{application_id}/interviews/", response={201: InterviewSchema, 404: dict, 400: dict}, tags=["Interviews"])
async def schedule_interview(request, application_id: str, payload: InterviewCreateSchema):
    """Schedule an interview for an application."""
    service = ApplicationService()
    try:
        interview = service.schedule_interview_minimal(
            application_id=application_id,
            round_name=payload.round_name,
            scheduled_start=datetime.fromisoformat(payload.scheduled_start.replace('Z', '+00:00')),
            scheduled_end=datetime.fromisoformat(payload.scheduled_end.replace('Z', '+00:00')),
            location_type=payload.location_type,
            location_details=payload.location_details
        )
    except Application.DoesNotExist:
        return 404, {"error": "Application not found"}
    except Exception as e:
        return 400, {"error": str(e)}

    return 201, InterviewSchema(
        id=str(interview.id),
        round_name=interview.round_name,
        scheduled_start=interview.scheduled_start.isoformat(),
        scheduled_end=interview.scheduled_end.isoformat(),
        location_type=interview.location_type,
        location_details=interview.location_details,
        outcome=interview.outcome
    )


@applications_router.get("/{application_id}/interviews/", response=List[InterviewSchema], tags=["Interviews"])
async def get_application_interviews(request, application_id: str):
    """Get interviews for an application."""
    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        return []

    interviews = application.interviews.all()
    return [
        InterviewSchema(
            id=str(interview.id),
            round_name=interview.round_name,
            scheduled_start=interview.scheduled_start.isoformat(),
            scheduled_end=interview.scheduled_end.isoformat(),
            location_type=interview.location_type,
            location_details=interview.location_details,
            outcome=interview.outcome
        )
        for interview in interviews
    ]


# -----------------------------
# Event History Endpoints
# -----------------------------

@applications_router.get("/{application_id}/events/", response=List[ApplicationEventSchema], tags=["Events"])
async def get_application_events(request, application_id: str):
    """Get event history for an application."""
    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        return []

    events = application.events.all()
    return [
        ApplicationEventSchema(
            id=str(event.id),
            event_type=event.event_type,
            metadata=event.metadata,
            created_at=event.created_at.isoformat(),
            actor_id=event.actor.id if event.actor else None
        )
        for event in events
    ]


# =====================================================
# CANDIDATE APPLICATION ENDPOINTS
# =====================================================

@applications_router.post("/apply", response={200: ApplicationSchema, 400: dict}, tags=["Applications"])
async def apply_to_opportunity(request, payload: ApplicationApplySchema):
    """Apply to an opportunity (requires authentication)."""
    from yeshuman.api import get_user_from_token
    from apps.profiles.models import Profile

    # Get current user and their profile
    user = await get_user_from_token(request)
    if not user:
        return 400, {"error": "Authentication required"}

    @sync_to_async
    def get_profile_id():
        try:
            return str(user.profile.id)
        except:
            return None

    profile_id = await get_profile_id()
    if not profile_id:
        return 400, {"error": "Profile not found"}

    # Create application using service
    service = ApplicationService()
    try:
        result = await service.create_application(
            profile_id=profile_id,
            opportunity_id=payload.opportunity_id,
            source="direct",
            answers=payload.answers
        )
    except ValueError as e:
        return 400, {"error": str(e)}
    except Exception as e:
        return 400, {"error": f"Failed to create application: {str(e)}"}

    application = result.application

    return 200, ApplicationSchema(
        id=str(application.id),
        profile_id=str(application.profile.id),
        opportunity_title=application.opportunity.title,
        organisation_name=application.organisation.name,
        status=application.status,
        source=application.source,
        applied_at=application.applied_at.isoformat(),
        current_stage=ApplicationStageSchema(
            id=str(application.current_stage_instance.id),
            stage_name=application.current_stage_instance.stage_template.name,
            entered_at=application.current_stage_instance.entered_at.isoformat(),
            is_open=application.current_stage_instance.is_open
        ) if application.current_stage_instance else None
    )


@applications_router.get("/my", response=List[ApplicationSchema], tags=["Applications"])
async def list_my_applications(request):
    """List current user's applications."""
    from yeshuman.api import get_user_from_token
    from asgiref.sync import sync_to_async

    user = await get_user_from_token(request)
    if not user:
        return []

    @sync_to_async
    def get_applications_sync():
        return list(user.profile.applications.all().prefetch_related(
            'opportunity', 'organisation', 'current_stage_instance__stage_template'
        ))

    applications = await get_applications_sync()
    return [
        ApplicationSchema(
            id=str(app.id),
            profile_id=str(app.profile.id),
            opportunity_title=app.opportunity.title,
            organisation_name=app.organisation.name,
            status=app.status,
            source=app.source,
            applied_at=app.applied_at.isoformat(),
            current_stage=ApplicationStageSchema(
                id=str(app.current_stage_instance.id),
                stage_name=app.current_stage_instance.stage_template.name,
                entered_at=app.current_stage_instance.entered_at.isoformat(),
                is_open=app.current_stage_instance.is_open
            ) if app.current_stage_instance else None
        )
        for app in applications
    ]


# =====================================================
# EMPLOYER INVITATION ENDPOINTS
# =====================================================

@applications_router.post("/invite", response={200: ApplicationSchema, 400: dict, 403: dict}, tags=["Applications"])
async def invite_to_apply(request, payload: ApplicationInviteSchema):
    """Invite a profile to apply for an opportunity (employer only)."""
    from yeshuman.api import get_user_from_token
    from apps.organisations.api import check_employer_permissions

    user = await get_user_from_token(request)
    if not user:
        return 400, {"error": "Authentication required"}

    # Check employer permissions
    try:
        await check_employer_permissions(user)
    except:
        return 403, {"error": "Employer access required"}

    # Create invitation using service
    service = ApplicationService()
    try:
        application = await service.invite_profile_to_opportunity(
            profile_id=payload.profile_id,
            opportunity_id=payload.opportunity_id
        )
    except Exception as e:
        return 400, {"error": f"Failed to create invitation: {str(e)}"}

    return 200, ApplicationSchema(
        id=str(application.id),
        profile_id=str(application.profile.id),
        opportunity_title=application.opportunity.title,
        organisation_name=application.organisation.name,
        status=application.status,
        source=application.source,
        applied_at=application.applied_at.isoformat(),
        current_stage=None  # Invited applications don't have stages yet
    )


