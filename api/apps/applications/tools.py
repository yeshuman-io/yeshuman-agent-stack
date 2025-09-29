"""
Tools for applications app using LangChain BaseTool.
Provides tools for managing applications, stages, screening, and interviews.
"""

from typing import Optional, List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from pydantic import BaseModel, Field
from datetime import datetime

# Django imports
from asgiref.sync import sync_to_async

from apps.applications.services import ApplicationService
from apps.applications.models import Application, StageTemplate
from apps.profiles.models import Profile
from apps.opportunities.models import Opportunity
from apps.organisations.models import Organisation


# =====================================================
# APPLICATION MANAGEMENT TOOLS
# =====================================================

class CreateApplicationInput(BaseModel):
    """Input for creating an application."""
    profile_id: str = Field(description="UUID of the profile")
    opportunity_id: str = Field(description="UUID of the opportunity")
    source: str = Field(default="direct", description="Source of the application")


class CreateApplicationTool(BaseTool):
    """Tool for creating a new application."""

    name: str = "create_application"
    description: str = "Create a new application for a profile and opportunity. Returns the created application details."
    args_schema: type[BaseModel] = CreateApplicationInput

    def _run(self, profile_id: str, opportunity_id: str, source: str = "direct",
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the create application tool synchronously."""
        try:
            # For sync execution, we'll call the async method directly and handle the result
            # This is a simplified approach for testing - in production you'd want proper async handling
            import asyncio
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                service = ApplicationService()
                return await service.create_application(
                    profile_id=profile_id,
                    opportunity_id=opportunity_id,
                    source=source
                )

            result = run_service()

            if result.created:
                return f"✅ Application created successfully for profile {profile_id} and opportunity {opportunity_id}"
            else:
                return f"ℹ️ Application already exists for profile {profile_id} and opportunity {opportunity_id}"
        except Exception as e:
            return f"❌ Failed to create application: {str(e)}"

    async def _arun(self, profile_id: str, opportunity_id: str, source: str = "direct",
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the create application tool asynchronously."""
        try:
            service = ApplicationService()
            result = await service.create_application(
                profile_id=profile_id,
                opportunity_id=opportunity_id,
                source=source
            )

            if result.created:
                return f"✅ Application created successfully for profile {profile_id} and opportunity {opportunity_id}"
            else:
                return f"ℹ️ Application already exists for profile {profile_id} and opportunity {opportunity_id}"
        except Exception as e:
            return f"❌ Failed to create application: {str(e)}"


class ChangeApplicationStageInput(BaseModel):
    """Input for changing application stage."""
    application_id: str = Field(description="UUID of the application")
    stage_slug: str = Field(description="Slug of the target stage")
    actor_id: Optional[int] = Field(default=None, description="ID of the actor making the change")


class ChangeApplicationStageTool(BaseTool):
    """Tool for changing an application's stage."""

    name: str = "change_application_stage"
    description: str = "Change the stage of an application (e.g., applied, in_review, interview, offer, hired, rejected, withdrawn)."
    args_schema: type[BaseModel] = ChangeApplicationStageInput

    def _run(self, application_id: str, stage_slug: str, actor_id: Optional[int] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the change stage tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                service = ApplicationService()
                return await service.change_stage(
                    application_id=application_id,
                    stage_slug=stage_slug,
                    actor_id=actor_id
                )

            application = run_service()
            return f"✅ Application {application_id} moved to stage: {application.current_stage_instance.stage_template.name}"
        except Exception as e:
            return f"❌ Failed to change application stage: {str(e)}"

    async def _arun(self, application_id: str, stage_slug: str, actor_id: Optional[int] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the change stage tool asynchronously."""
        try:
            service = ApplicationService()
            application = await service.change_stage(
                application_id=application_id,
                stage_slug=stage_slug,
                actor_id=actor_id
            )
            return f"✅ Application {application_id} moved to stage: {application.current_stage_instance.stage_template.name}"
        except Exception as e:
            return f"❌ Failed to change application stage: {str(e)}"


class RecordApplicationDecisionInput(BaseModel):
    """Input for recording an application decision."""
    application_id: str = Field(description="UUID of the application")
    status: str = Field(description="Decision status (hired, rejected, offer)")
    reason: Optional[str] = Field(default=None, description="Optional reason for the decision")


class RecordApplicationDecisionTool(BaseTool):
    """Tool for recording final decisions on applications."""

    name: str = "record_application_decision"
    description: str = "Record a final decision on an application (hired, rejected, or offer)."
    args_schema: type[BaseModel] = RecordApplicationDecisionInput

    def _run(self, application_id: str, status: str, reason: Optional[str] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the record decision tool synchronously."""
        try:
            def run_async_service():
                service = ApplicationService()
                return service.record_decision(
                    application_id=application_id,
                    status=status,
                    reason_text=reason
                )

            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            application = loop.run_until_complete(sync_to_async(run_async_service)())
            return f"✅ Application {application_id} decision recorded: {status}"
        except Exception as e:
            return f"❌ Failed to record application decision: {str(e)}"

    async def _arun(self, application_id: str, status: str, reason: Optional[str] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the record decision tool asynchronously."""
        try:
            service = ApplicationService()
            application = await service.record_decision(
                application_id=application_id,
                status=status,
                reason_text=reason
            )
            return f"✅ Application {application_id} decision recorded: {status}"
        except Exception as e:
            return f"❌ Failed to record application decision: {str(e)}"


# =====================================================
# SCREENING TOOLS
# =====================================================

class UpsertScreeningQuestionInput(BaseModel):
    """Input for creating/updating screening questions."""
    opportunity_id: str = Field(description="UUID of the opportunity")
    question_text: str = Field(description="The question text")
    question_type: str = Field(description="Type of question (text, boolean, single_choice, multi_choice, number)")
    is_required: bool = Field(default=False, description="Whether the question is required")
    order: Optional[int] = Field(default=None, description="Order of the question")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Additional configuration")
    question_id: Optional[str] = Field(default=None, description="Question ID for updates")


class UpsertScreeningQuestionTool(BaseTool):
    """Tool for creating or updating screening questions."""

    name: str = "upsert_screening_question"
    description: str = "Create or update a screening question for an opportunity."
    args_schema: type[BaseModel] = UpsertScreeningQuestionInput

    def _run(self, opportunity_id: str, question_text: str, question_type: str,
             is_required: bool = False, order: Optional[int] = None,
             config: Optional[Dict[str, Any]] = None, question_id: Optional[str] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the upsert screening question tool synchronously."""
        try:
            def run_async_service():
                service = ApplicationService()
                payload = {
                    "id": question_id,
                    "question_text": question_text,
                    "question_type": question_type,
                    "is_required": is_required,
                    "order": order,
                    "config": config or {}
                }
                return service.upsert_screening_question(opportunity_id, payload)

            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            question = loop.run_until_complete(sync_to_async(run_async_service)())
            action = "updated" if question_id else "created"
            return f"✅ Screening question {action}: {question.question_text}"
        except Exception as e:
            return f"❌ Failed to upsert screening question: {str(e)}"

    async def _arun(self, opportunity_id: str, question_text: str, question_type: str,
                   is_required: bool = False, order: Optional[int] = None,
                   config: Optional[Dict[str, Any]] = None, question_id: Optional[str] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the upsert screening question tool asynchronously."""
        try:
            service = ApplicationService()
            payload = {
                "id": question_id,
                "question_text": question_text,
                "question_type": question_type,
                "is_required": is_required,
                "order": order,
                "config": config or {}
            }
            question = await service.upsert_screening_question(opportunity_id, payload)
            action = "updated" if question_id else "created"
            return f"✅ Screening question {action}: {question.question_text}"
        except Exception as e:
            return f"❌ Failed to upsert screening question: {str(e)}"


class DeleteScreeningQuestionInput(BaseModel):
    """Input for deleting screening questions."""
    question_id: str = Field(description="UUID of the question to delete")


class DeleteScreeningQuestionTool(BaseTool):
    """Tool for deleting screening questions."""

    name: str = "delete_screening_question"
    description: str = "Delete a screening question from an opportunity."
    args_schema: type[BaseModel] = DeleteScreeningQuestionInput

    def _run(self, question_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the delete screening question tool synchronously."""
        try:
            def run_async_service():
                service = ApplicationService()
                return service.delete_screening_question(question_id)

            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(sync_to_async(run_async_service)())
            return f"✅ Screening question {question_id} deleted"
        except Exception as e:
            return f"❌ Failed to delete screening question: {str(e)}"

    async def _arun(self, question_id: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the delete screening question tool asynchronously."""
        try:
            service = ApplicationService()
            await service.delete_screening_question(question_id)
            return f"✅ Screening question {question_id} deleted"
        except Exception as e:
            return f"❌ Failed to delete screening question: {str(e)}"


class SubmitApplicationAnswersInput(BaseModel):
    """Input for submitting application answers."""
    application_id: str = Field(description="UUID of the application")
    answers: List[Dict[str, Any]] = Field(description="List of answers with question_id and answer data")


class SubmitApplicationAnswersTool(BaseTool):
    """Tool for submitting screening answers."""

    name: str = "submit_application_answers"
    description: str = "Submit answers to screening questions for an application."
    args_schema: type[BaseModel] = SubmitApplicationAnswersInput

    def _run(self, application_id: str, answers: List[Dict[str, Any]],
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the submit answers tool synchronously."""
        @sync_to_async
        def run_async_service():
            service = ApplicationService()
            return service.submit_answers(application_id, answers)

        try:
            answer_objects = run_async_service()
            return f"✅ Submitted {len(answer_objects)} answers for application {application_id}"
        except Exception as e:
            return f"❌ Failed to submit application answers: {str(e)}"

    async def _arun(self, application_id: str, answers: List[Dict[str, Any]],
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the submit answers tool asynchronously."""
        try:
            service = ApplicationService()
            answer_objects = await service.submit_answers(application_id, answers)
            return f"✅ Submitted {len(answer_objects)} answers for application {application_id}"
        except Exception as e:
            return f"❌ Failed to submit application answers: {str(e)}"


# =====================================================
# STAGE MANAGEMENT TOOLS
# =====================================================

class SeedStagesTool(BaseTool):
    """Tool for seeding default application stages."""

    name: str = "seed_application_stages"
    description: str = "Seed the database with default application stages (applied, in_review, interview, offer, hired, rejected, withdrawn)."

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the seed stages tool synchronously."""
        @sync_to_async
        def run_async_service():
            service = ApplicationService()
            return service.seed_default_stages()

        try:
            stages = run_async_service()
            return f"✅ Seeded {len(stages)} default application stages"
        except Exception as e:
            return f"❌ Failed to seed application stages: {str(e)}"

    async def _arun(self, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the seed stages tool asynchronously."""
        try:
            service = ApplicationService()
            stages = await service.seed_default_stages()
            return f"✅ Seeded {len(stages)} default application stages"
        except Exception as e:
            return f"❌ Failed to seed application stages: {str(e)}"


class ListStagesTool(BaseTool):
    """Tool for listing available application stages."""

    name: str = "list_application_stages"
    description: str = "List all available application stages with their details."

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the list stages tool synchronously."""
        @sync_to_async
        def run_async_service():
            service = ApplicationService()
            return service.list_stages()

        try:
            stages = run_async_service()
            stage_list = [f"- {stage.name} ({stage.slug}) - Order: {stage.order}, Terminal: {stage.is_terminal}"
                         for stage in stages]
            return f"📋 Available Application Stages:\n" + "\n".join(stage_list)
        except Exception as e:
            return f"❌ Failed to list application stages: {str(e)}"

    async def _arun(self, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the list stages tool asynchronously."""
        try:
            service = ApplicationService()
            stages = await service.list_stages()
            stage_list = [f"- {stage.name} ({stage.slug}) - Order: {stage.order}, Terminal: {stage.is_terminal}"
                         for stage in stages]
            return f"📋 Available Application Stages:\n" + "\n".join(stage_list)
        except Exception as e:
            return f"❌ Failed to list application stages: {str(e)}"


class UpsertStageInput(BaseModel):
    """Input for creating/updating application stages."""
    name: str = Field(description="Name of the stage")
    slug: str = Field(description="Slug identifier for the stage")
    order: int = Field(description="Order/sequence of the stage")
    is_terminal: bool = Field(default=False, description="Whether this is a terminal stage")
    stage_id: Optional[str] = Field(default=None, description="Stage ID for updates")


class UpsertStageTool(BaseTool):
    """Tool for creating or updating application stages."""

    name: str = "upsert_application_stage"
    description: str = "Create or update an application stage."
    args_schema: type[BaseModel] = UpsertStageInput

    def _run(self, name: str, slug: str, order: int, is_terminal: bool = False,
             stage_id: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the upsert stage tool synchronously."""
        @sync_to_async
        def run_async_service():
            service = ApplicationService()
            payload = {
                "id": stage_id,
                "name": name,
                "slug": slug,
                "order": order,
                "is_terminal": is_terminal
            }
            return service.upsert_stage_template(payload)

        try:
            stage = run_async_service()
            action = "updated" if stage_id else "created"
            return f"✅ Application stage {action}: {stage.name} ({stage.slug})"
        except Exception as e:
            return f"❌ Failed to upsert application stage: {str(e)}"

    async def _arun(self, name: str, slug: str, order: int, is_terminal: bool = False,
                   stage_id: Optional[str] = None, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the upsert stage tool asynchronously."""
        try:
            service = ApplicationService()
            payload = {
                "id": stage_id,
                "name": name,
                "slug": slug,
                "order": order,
                "is_terminal": is_terminal
            }
            stage = await service.upsert_stage_template(payload)
            action = "updated" if stage_id else "created"
            return f"✅ Application stage {action}: {stage.name} ({stage.slug})"
        except Exception as e:
            return f"❌ Failed to upsert application stage: {str(e)}"


class DeleteStageInput(BaseModel):
    """Input for deleting application stages."""
    identifier: str = Field(description="Stage ID or slug to delete")


class DeleteStageTool(BaseTool):
    """Tool for deleting application stages."""

    name: str = "delete_application_stage"
    description: str = "Delete an application stage by ID or slug."
    args_schema: type[BaseModel] = DeleteStageInput

    def _run(self, identifier: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the delete stage tool synchronously."""
        @sync_to_async
        def run_async_service():
            service = ApplicationService()
            return service.delete_stage_template(identifier)

        try:
            deleted_count = run_async_service()
            return f"✅ Deleted {deleted_count} application stage(s)"
        except Exception as e:
            return f"❌ Failed to delete application stage: {str(e)}"

    async def _arun(self, identifier: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the delete stage tool asynchronously."""
        try:
            service = ApplicationService()
            deleted_count = await service.delete_stage_template(identifier)
            return f"✅ Deleted {deleted_count} application stage(s)"
        except Exception as e:
            return f"❌ Failed to delete application stage: {str(e)}"


# =====================================================
# INTERVIEW TOOLS
# =====================================================

class ScheduleInterviewInput(BaseModel):
    """Input for scheduling interviews."""
    application_id: str = Field(description="UUID of the application")
    round_name: str = Field(description="Name of the interview round")
    scheduled_start: str = Field(description="Start time in ISO format")
    scheduled_end: str = Field(description="End time in ISO format")
    location_type: str = Field(default="virtual", description="Location type (virtual, in_person, phone)")
    location_details: str = Field(default="", description="Additional location details")


class ScheduleInterviewTool(BaseTool):
    """Tool for scheduling interviews."""

    name: str = "schedule_interview"
    description: str = "Schedule an interview for an application."
    args_schema: type[BaseModel] = ScheduleInterviewInput

    def _run(self, application_id: str, round_name: str, scheduled_start: str,
             scheduled_end: str, location_type: str = "virtual", location_details: str = "",
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the schedule interview tool synchronously."""
        @sync_to_async
        def run_async_service():
            service = ApplicationService()
            start_dt = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(scheduled_end.replace('Z', '+00:00'))

            return service.schedule_interview_minimal(
                application_id=application_id,
                round_name=round_name,
                scheduled_start=start_dt,
                scheduled_end=end_dt,
                location_type=location_type,
                location_details=location_details
            )

        try:
            interview = run_async_service()
            return f"✅ Interview scheduled: {round_name} for application {application_id}"
        except Exception as e:
            return f"❌ Failed to schedule interview: {str(e)}"

    async def _arun(self, application_id: str, round_name: str, scheduled_start: str,
                   scheduled_end: str, location_type: str = "virtual", location_details: str = "",
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the schedule interview tool asynchronously."""
        try:
            service = ApplicationService()
            start_dt = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(scheduled_end.replace('Z', '+00:00'))

            interview = await service.schedule_interview_minimal(
                application_id=application_id,
                round_name=round_name,
                scheduled_start=start_dt,
                scheduled_end=end_dt,
                location_type=location_type,
                location_details=location_details
            )
            return f"✅ Interview scheduled: {round_name} for application {application_id}"
        except Exception as e:
            return f"❌ Failed to schedule interview: {str(e)}"


class ListScreeningQuestionsInput(BaseModel):
    """Input for listing screening questions."""
    opportunity_id: str = Field(description="UUID of the opportunity")


class ListScreeningQuestionsTool(BaseTool):
    """Tool for listing screening questions for an opportunity."""

    name: str = "list_screening_questions"
    description: str = "List all screening questions for a specific opportunity."
    args_schema: type[BaseModel] = ListScreeningQuestionsInput

    def _run(self, opportunity_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the list screening questions tool synchronously."""
        try:
            from apps.applications.models import OpportunityQuestion
            questions = list(OpportunityQuestion.objects.filter(opportunity_id=opportunity_id).order_by("order"))
            if not questions:
                return f"📋 No screening questions found for opportunity {opportunity_id}"

            question_list = [f"- {q.question_text} ({q.question_type}) - Required: {q.is_required}, Order: {q.order}"
                           for q in questions]
            return f"📋 Screening Questions for Opportunity {opportunity_id}:\n" + "\n".join(question_list)
        except Exception as e:
            return f"❌ Failed to list screening questions: {str(e)}"

    async def _arun(self, opportunity_id: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the list screening questions tool asynchronously."""
        try:
            from apps.applications.models import OpportunityQuestion
            questions = list(await sync_to_async(
                lambda: list(OpportunityQuestion.objects.filter(opportunity_id=opportunity_id).order_by("order"))
            )())
            if not questions:
                return f"📋 No screening questions found for opportunity {opportunity_id}"

            question_list = [f"- {q.question_text} ({q.question_type}) - Required: {q.is_required}, Order: {q.order}"
                           for q in questions]
            return f"📋 Screening Questions for Opportunity {opportunity_id}:\n" + "\n".join(question_list)
        except Exception as e:
            return f"❌ Failed to list screening questions: {str(e)}"


# =====================================================
# BULK OPERATIONS
# =====================================================

class BulkChangeStageInput(BaseModel):
    """Input for bulk stage changes."""
    application_ids: List[str] = Field(description="List of application UUIDs")
    stage_slug: str = Field(description="Target stage slug")


class BulkChangeStageTool(BaseTool):
    """Tool for changing stages of multiple applications at once."""

    name: str = "bulk_change_application_stage"
    description: str = "Change the stage of multiple applications at once."
    args_schema: type[BaseModel] = BulkChangeStageInput

    def _run(self, application_ids: List[str], stage_slug: str,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the bulk change stage tool synchronously."""
        try:
            service = ApplicationService()
            results = []
            successes = 0
            failures = 0

            for app_id in application_ids:
                try:
                    application = service.change_stage(app_id, stage_slug)
                    results.append(f"✅ {app_id}: {application.current_stage_instance.stage_template.name}")
                    successes += 1
                except Exception as e:
                    results.append(f"❌ {app_id}: {str(e)}")
                    failures += 1

            summary = f"📊 Bulk Stage Change Results: {successes} succeeded, {failures} failed\n"
            summary += "\n".join(results[:10])  # Show first 10 results
            if len(results) > 10:
                summary += f"\n... and {len(results) - 10} more"

            return summary
        except Exception as e:
            return f"❌ Failed to execute bulk stage change: {str(e)}"

    async def _arun(self, application_ids: List[str], stage_slug: str,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the bulk change stage tool asynchronously."""
        try:
            service = ApplicationService()
            results = []
            successes = 0
            failures = 0

            for app_id in application_ids:
                try:
                    application = await service.change_stage(app_id, stage_slug)
                    results.append(f"✅ {app_id}: {application.current_stage_instance.stage_template.name}")
                    successes += 1
                except Exception as e:
                    results.append(f"❌ {app_id}: {str(e)}")
                    failures += 1

            summary = f"📊 Bulk Stage Change Results: {successes} succeeded, {failures} failed\n"
            summary += "\n".join(results[:10])  # Show first 10 results
            if len(results) > 10:
                summary += f"\n... and {len(results) - 10} more"

            return summary
        except Exception as e:
            return f"❌ Failed to execute bulk stage change: {str(e)}"


# =====================================================
# APPLICATION LISTING TOOLS
# =====================================================

class ListApplicationsForProfileInput(BaseModel):
    """Input for listing applications for a profile."""
    profile_id: str = Field(description="Profile UUID")
    status: Optional[str] = Field(default=None, description="Optional status filter")
    limit: Optional[int] = Field(default=50, description="Max to list")


class ListApplicationsForProfileTool(BaseTool):
    """Tool for listing applications for a specific profile."""

    name: str = "list_applications_for_profile"
    description: str = "List applications for a profile with stage/status summary."
    args_schema: type[BaseModel] = ListApplicationsForProfileInput

    def _run(self, profile_id: str, status: Optional[str] = None, limit: Optional[int] = 50,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the list applications for profile tool synchronously."""
        @sync_to_async
        def fetch_applications():
            from apps.applications.models import Application
            qs = Application.objects.select_related(
                'opportunity__organisation',
                'current_stage_instance__stage_template'
            ).filter(profile_id=profile_id).order_by('-applied_at')

            if status:
                qs = qs.filter(status=status)

            return list(qs[: (limit or 50)])

        try:
            apps = fetch_applications()
            if not apps:
                return "No applications for this profile."

            lines = [
                f"{a.opportunity.title} @ {a.opportunity.organisation.name} id={a.id} status={a.status} stage={(a.current_stage_instance.stage_template.slug if a.current_stage_instance else 'none')}"
                for a in apps
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Failed to list applications for profile: {str(e)}"

    async def _arun(self, profile_id: str, status: Optional[str] = None, limit: Optional[int] = 50,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the list applications for profile tool asynchronously."""
        try:
            def fetch_applications():
                from apps.applications.models import Application
                qs = Application.objects.select_related(
                    'opportunity__organisation',
                    'current_stage_instance__stage_template'
                ).filter(profile_id=profile_id).order_by('-applied_at')

                if status:
                    qs = qs.filter(status=status)

                return list(qs[: (limit or 50)])

            apps = await sync_to_async(fetch_applications)()

            if not apps:
                return "No applications for this profile."

            lines = [
                f"{a.opportunity.title} @ {a.opportunity.organisation.name} id={a.id} status={a.status} stage={(a.current_stage_instance.stage_template.slug if a.current_stage_instance else 'none')}"
                for a in apps
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Failed to list applications for profile: {str(e)}"


class ListApplicationsForOpportunityInput(BaseModel):
    """Input for listing applications for an opportunity."""
    opportunity_id: str = Field(description="Opportunity UUID")
    status: Optional[str] = Field(default=None, description="Optional status filter")
    limit: Optional[int] = Field(default=50, description="Max to list")


class ListApplicationsForOpportunityTool(BaseTool):
    """Tool for listing applications for a specific opportunity."""

    name: str = "list_applications_for_opportunity"
    description: str = "List applications for an opportunity with stage/status summary."
    args_schema: type[BaseModel] = ListApplicationsForOpportunityInput

    def _run(self, opportunity_id: str, status: Optional[str] = None, limit: Optional[int] = 50,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the list applications for opportunity tool synchronously."""
        @sync_to_async
        def fetch_applications():
            from apps.applications.models import Application
            qs = Application.objects.select_related(
                'profile',
                'current_stage_instance__stage_template'
            ).filter(opportunity_id=opportunity_id).order_by('-applied_at')

            if status:
                qs = qs.filter(status=status)

            return list(qs[: (limit or 50)])

        try:
            apps = fetch_applications()
            if not apps:
                return "No applications for this opportunity."

            lines = [
                f"{a.profile.first_name} {a.profile.last_name} id={a.id} status={a.status} stage={(a.current_stage_instance.stage_template.slug if a.current_stage_instance else 'none')}"
                for a in apps
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Failed to list applications for opportunity: {str(e)}"

    async def _arun(self, opportunity_id: str, status: Optional[str] = None, limit: Optional[int] = 50,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the list applications for opportunity tool asynchronously."""
        try:
            def fetch_applications():
                from apps.applications.models import Application
                qs = Application.objects.select_related(
                    'profile',
                    'current_stage_instance__stage_template'
                ).filter(opportunity_id=opportunity_id).order_by('-applied_at')

                if status:
                    qs = qs.filter(status=status)

                return list(qs[: (limit or 50)])

            apps = await sync_to_async(fetch_applications)()

            if not apps:
                return "No applications for this opportunity."

            lines = [
                f"{a.profile.first_name} {a.profile.last_name} id={a.id} status={a.status} stage={(a.current_stage_instance.stage_template.slug if a.current_stage_instance else 'none')}"
                for a in apps
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Failed to list applications for opportunity: {str(e)}"


class GetApplicationDetailsInput(BaseModel):
    """Input for getting application details."""
    application_id: str = Field(description="Application UUID")


class GetApplicationDetailsTool(BaseTool):
    """Tool for getting full details of a specific application."""

    name: str = "get_application_details"
    description: str = "Show full details for an application (answers, interviews)."
    args_schema: type[BaseModel] = GetApplicationDetailsInput

    def _run(self, application_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the get application details tool synchronously."""
        @sync_to_async
        def fetch_application():
            from apps.applications.models import Application
            return Application.objects.select_related(
                'profile',
                'opportunity__organisation',
                'current_stage_instance__stage_template'
            ).prefetch_related('answers__question', 'interviews').get(id=application_id)

        try:
            application = fetch_application()
            return self._format_application_details(application)
        except Exception as e:
            return f"❌ Application {application_id} not found: {str(e)}"

    async def _arun(self, application_id: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the get application details tool asynchronously."""
        try:
            def fetch_application():
                from apps.applications.models import Application
                return Application.objects.select_related(
                    'profile',
                    'opportunity__organisation',
                    'current_stage_instance__stage_template'
                ).prefetch_related('answers__question', 'interviews').get(id=application_id)

            application = await sync_to_async(fetch_application)()
            return self._format_application_details(application)
        except Exception as e:
            return f"❌ Application {application_id} not found: {str(e)}"

    def _format_application_details(self, application) -> str:
        """Format application details for display."""
        lines = [
            f"Application {application.id}",
            f"Status: {application.status} | Stage: {(application.current_stage_instance.stage_template.slug if application.current_stage_instance else 'none')}",
            f"Profile: {application.profile.first_name} {application.profile.last_name} <{application.profile.email}>",
            f"Opportunity: {application.opportunity.title} @ {application.opportunity.organisation.name}",
            "Answers:",
        ]

        for ans in application.answers.all():
            lines.append(f"- Q({ans.question.question_type}) {'*' if ans.question.is_required else ''} {ans.question.question_text} -> disq={ans.is_disqualifying}")

        lines.append("Interviews:")
        for iv in application.interviews.all():
            lines.append(f"- {iv.round_name} {iv.scheduled_start.isoformat()} - {iv.scheduled_end.isoformat()} {iv.location_type} outcome={iv.outcome}")

        return "\n".join(lines)


# =====================================================
# EXPORT ALL APPLICATION TOOLS
# =====================================================

# Core Application Management Tools (basic application operations)
APPLICATION_CORE_TOOLS = [
    CreateApplicationTool(),
    ChangeApplicationStageTool(),
    RecordApplicationDecisionTool(),
]

# Screening and Assessment Tools (questions, answers, evaluation)
APPLICATION_SCREENING_TOOLS = [
    UpsertScreeningQuestionTool(),
    DeleteScreeningQuestionTool(),
    SubmitApplicationAnswersTool(),
    ListScreeningQuestionsTool(),
]

# Stage Management Tools (workflow and pipeline management)
APPLICATION_STAGE_TOOLS = [
    SeedStagesTool(),
    ListStagesTool(),
    UpsertStageTool(),
    DeleteStageTool(),
]

# Interview and Scheduling Tools
APPLICATION_INTERVIEW_TOOLS = [
    ScheduleInterviewTool(),
]

# Bulk Operations Tools (batch processing)
APPLICATION_BULK_TOOLS = [
    BulkChangeStageTool(),
]

# Application Discovery Tools (searching and listing)
APPLICATION_DISCOVERY_TOOLS = [
    ListApplicationsForProfileTool(),
    ListApplicationsForOpportunityTool(),
    GetApplicationDetailsTool(),
]

# Combined application tools for general use
APPLICATION_TOOLS = (
    APPLICATION_CORE_TOOLS +
    APPLICATION_SCREENING_TOOLS +
    APPLICATION_STAGE_TOOLS +
    APPLICATION_INTERVIEW_TOOLS +
    APPLICATION_BULK_TOOLS +
    APPLICATION_DISCOVERY_TOOLS
)

__all__ = [
    'APPLICATION_TOOLS',
    'APPLICATION_CORE_TOOLS',
    'APPLICATION_SCREENING_TOOLS',
    'APPLICATION_STAGE_TOOLS',
    'APPLICATION_INTERVIEW_TOOLS',
    'APPLICATION_BULK_TOOLS',
    'APPLICATION_DISCOVERY_TOOLS',
    'CreateApplicationTool',
    'ChangeApplicationStageTool',
    'RecordApplicationDecisionTool',
    'UpsertScreeningQuestionTool',
    'DeleteScreeningQuestionTool',
    'SubmitApplicationAnswersTool',
    'ListScreeningQuestionsTool',
    'SeedStagesTool',
    'ListStagesTool',
    'UpsertStageTool',
    'DeleteStageTool',
    'ScheduleInterviewTool',
    'BulkChangeStageTool',
    'ListApplicationsForProfileTool',
    'ListApplicationsForOpportunityTool',
    'GetApplicationDetailsTool',
]
