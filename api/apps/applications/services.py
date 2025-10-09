from __future__ import annotations

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.applications.models import (
    Application,
    StageTemplate,
    ApplicationStageInstance,
    ApplicationEvent,
    OpportunityQuestion,
    ApplicationAnswer,
    Interview,
)
from apps.opportunities.models import Opportunity
from apps.organisations.models import Organisation
from apps.profiles.models import Profile
from apps.evaluations.models import Evaluation
from apps.evaluations.services import EvaluationService


@dataclass
class CreateApplicationResult:
    application: Application
    created: bool


class ApplicationService:
    """Service methods for ATS operations."""

    # -----------------------------
    # Stage management (global)
    # -----------------------------
    @transaction.atomic
    def seed_default_stages(self) -> List[StageTemplate]:
        """Ensure global default stages exist with sane order and terminal flags."""
        defaults = [
            ("applied", "Applied", 0, False),
            ("in_review", "In Review", 10, False),
            ("interview", "Interview", 20, False),
            ("offer", "Offer", 30, False),
            ("hired", "Hired", 100, True),
            ("rejected", "Rejected", 100, True),
            ("withdrawn", "Withdrawn", 100, True),
        ]
        stages: List[StageTemplate] = []
        for slug, name, order, is_terminal in defaults:
            obj, _ = StageTemplate.objects.get_or_create(slug=slug, defaults={
                "name": name,
                "order": order,
                "is_terminal": is_terminal,
            })
            # Keep fields up to date if they changed
            changed = False
            if obj.name != name:
                obj.name = name; changed = True
            if obj.order != order:
                obj.order = order; changed = True
            if obj.is_terminal != is_terminal:
                obj.is_terminal = is_terminal; changed = True
            if changed:
                obj.save()
            stages.append(obj)
        return stages

    def list_stages(self) -> List[StageTemplate]:
        return list(StageTemplate.objects.order_by("order", "name"))

    @transaction.atomic
    def upsert_stage_template(self, payload: Dict[str, Any]) -> StageTemplate:
        """Create or update a StageTemplate. Identified by id or slug."""
        sid = payload.get("id")
        slug = payload.get("slug")
        name = payload.get("name")
        order = payload.get("order")
        is_terminal = payload.get("is_terminal")

        if sid:
            st = StageTemplate.objects.get(id=sid)
            if slug is not None:
                st.slug = slug
            if name is not None:
                st.name = name
            if order is not None:
                st.order = int(order)
            if is_terminal is not None:
                st.is_terminal = bool(is_terminal)
            st.save()
            return st
        elif slug:
            st, created = StageTemplate.objects.get_or_create(slug=slug, defaults={
                "name": name or slug.replace("_", " ").title(),
                "order": int(order) if order is not None else 0,
                "is_terminal": bool(is_terminal) if is_terminal is not None else False,
            })
            if not created:
                if name is not None:
                    st.name = name
                if order is not None:
                    st.order = int(order)
                if is_terminal is not None:
                    st.is_terminal = bool(is_terminal)
                st.save()
            return st
        else:
            raise ValueError("Provide either 'id' or 'slug' to upsert StageTemplate")

    @transaction.atomic
    def delete_stage_template(self, identifier: str) -> int:
        """Delete a StageTemplate by id (UUID) or slug. Returns count deleted."""
        from uuid import UUID
        try:
            UUID(str(identifier))
            qs = StageTemplate.objects.filter(id=identifier)
        except Exception:
            qs = StageTemplate.objects.filter(slug=identifier)
        deleted, _ = qs.delete()
        return deleted

    # -----------------------------
    # Applications
    # -----------------------------
    async def create_application(
        self,
        profile_id: str,
        opportunity_id: str,
        source: str = "direct",
        answers: Optional[List[Dict[str, Any]]] = None,
    ) -> CreateApplicationResult:
        """
        Create an application, validate screening, snapshot evaluation.
        Enforces unique(profile, opportunity).
        """
        @sync_to_async
        def _create_application_sync():
            with transaction.atomic():
                profile = Profile.objects.get(id=profile_id)
                opportunity = Opportunity.objects.select_related("organisation").get(id=opportunity_id)

                # Enforce no reapply
                existing = Application.objects.filter(profile=profile, opportunity=opportunity).first()
                if existing:
                    return CreateApplicationResult(application=existing, created=False)

                # Check if screening questions exist and require answers
                opportunity_questions = opportunity.opportunity_questions.all()
                if opportunity_questions.exists() and not answers:
                    raise ValueError("Screening answers are required for this opportunity")

                application = Application.objects.create(
                    profile=profile,
                    opportunity=opportunity,
                    organisation=opportunity.organisation,
                    source=source,
                    status="applied",
                )

                # Initial stage instance (first global stage if exists)
                first_stage = StageTemplate.objects.order_by("order").first()
                if first_stage:
                    stage_inst = ApplicationStageInstance.objects.create(
                        application=application,
                        stage_template=first_stage,
                    )
                    application.current_stage_instance = stage_inst
                    application.save(update_fields=["current_stage_instance"])
                    ApplicationEvent.objects.create(
                        application=application,
                        event_type="applied",
                        metadata={"stage": first_stage.slug},
                    )
                else:
                    ApplicationEvent.objects.create(
                        application=application,
                        event_type="applied",
                        metadata={}
                    )

                # Validate screening answers if provided
                if answers:
                    self.submit_answers(application.id, answers)

                # Snapshot evaluation
                eval_service = EvaluationService()
                # Create or locate evaluation record for this pair
                eval_set = eval_service.create_candidate_evaluation_set(opportunity_id)
                evaluation = eval_set.evaluations.filter(profile=profile, opportunity=opportunity).first()
                if evaluation:
                    application.evaluation = evaluation
                    application.evaluation_snapshot = {
                        "final_score": float(evaluation.final_score),
                        "rank_in_set": evaluation.rank_in_set,
                        "component_scores": evaluation.component_scores,
                        "was_llm_judged": evaluation.was_llm_judged,
                        "llm_reasoning": evaluation.llm_reasoning,
                    }
                    application.save(update_fields=["evaluation", "evaluation_snapshot"])

                return CreateApplicationResult(application=application, created=True)

        return await _create_application_sync()

    async def invite_profile_to_opportunity(self, profile_id: str, opportunity_id: str) -> Application:
        """
        Invite a profile to apply for an opportunity.
        Creates an application with status 'invited' if one doesn't exist.
        """
        @sync_to_async
        def _invite_sync():
            with transaction.atomic():
                profile = Profile.objects.get(id=profile_id)
                opportunity = Opportunity.objects.select_related("organisation").get(id=opportunity_id)

                # Check if application already exists
                existing = Application.objects.filter(profile=profile, opportunity=opportunity).first()
                if existing:
                    # If already invited or applied, return existing
                    return existing

                # Create invited application
                application = Application.objects.create(
                    profile=profile,
                    opportunity=opportunity,
                    organisation=opportunity.organisation,
                    source="referral",
                    status="invited",
                )

                # Create invitation event
                ApplicationEvent.objects.create(
                    application=application,
                    event_type="invited",
                    metadata={}
                )

                return application

        return await _invite_sync()

    async def change_stage(self, application_id: str, stage_slug: str, actor_id: Optional[int] = None) -> Application:
        @sync_to_async
        def change_stage_sync():
            with transaction.atomic():
                application = Application.objects.select_related("current_stage_instance").get(id=application_id)

                # Normalize and alias slugs
                slug = (stage_slug or "").strip().lower().replace(" ", "_")
                alias = {
                    "under-review": "in_review",
                    "under_review": "in_review",
                    "in-review": "in_review",
                    "screening": "in_review",
                    "review": "in_review",
                }
                slug = alias.get(slug, slug)

                next_stage = StageTemplate.objects.get(slug=slug)

                # Close current stage instance if open
                if application.current_stage_instance and application.current_stage_instance.is_open:
                    application.current_stage_instance.close()

                # Open new stage instance
                new_inst = ApplicationStageInstance.objects.create(
                    application=application,
                    stage_template=next_stage,
                    entered_by_id=actor_id,
                )
                application.current_stage_instance = new_inst

                # Update status for terminal stages
                if next_stage.is_terminal:
                    # Simple mapping: terminal named "hired" -> hired, else rejected/withdrawn
                    if next_stage.slug == "hired":
                        application.status = "hired"
                    elif next_stage.slug == "withdrawn":
                        application.status = "withdrawn"
                    else:
                        application.status = "rejected"
                else:
                    # Non-terminal heuristic status based on slug
                    if next_stage.slug.startswith("interview"):
                        application.status = "interview"
                    elif next_stage.slug == "offer":
                        application.status = "offer"
                    elif next_stage.slug in ("applied", "screening", "review", "in-review", "in_review"):
                        application.status = "in_review"
                    else:
                        application.status = "in_review"

                application.save()

                ApplicationEvent.objects.create(
                    application=application,
                    event_type="stage_changed",
                    metadata={"to_stage": next_stage.slug},
                    actor_id=actor_id,
                )

                return application

        return await change_stage_sync()

    async def withdraw_application(self, application_id: str, reason: Optional[str] = None) -> Application:
        @sync_to_async
        def withdraw_application_sync():
            with transaction.atomic():
                application = Application.objects.get(id=application_id)
                application.status = "withdrawn"
                if application.current_stage_instance and application.current_stage_instance.is_open:
                    application.current_stage_instance.close()
                application.save(update_fields=["status"])

                ApplicationEvent.objects.create(
                    application=application,
                    event_type="withdrawn",
                    metadata={"reason": reason} if reason else {},
                )
                return application

        return await withdraw_application_sync()

    async def record_decision(self, application_id: str, status: str, reason_text: Optional[str] = None) -> Application:
        @sync_to_async
        def record_decision_sync():
            with transaction.atomic():
                assert status in ("hired", "rejected", "offer"), "Invalid decision status"
                application = Application.objects.get(id=application_id)
                application.status = status
                application.save(update_fields=["status"])
                ApplicationEvent.objects.create(
                    application=application,
                    event_type="decision_made",
                    metadata={"status": status, "reason": reason_text} if reason_text else {"status": status},
                )
                return application

        return await record_decision_sync()

    async def upsert_screening_question(self, opportunity_id: str, payload: Dict[str, Any]) -> OpportunityQuestion:
        @sync_to_async
        def upsert_question_sync():
            with transaction.atomic():
                opp = Opportunity.objects.get(id=opportunity_id)
                qid = payload.get("id")
                if qid:
                    question = OpportunityQuestion.objects.get(id=qid, opportunity=opp)
                    for field in ["question_text", "question_type", "is_required", "order", "config"]:
                        if field in payload and payload[field] is not None:
                            setattr(question, field, payload[field])
                    question.save()
                    return question
                else:
                    return OpportunityQuestion.objects.create(
                        opportunity=opp,
                        question_text=payload["question_text"],
                        question_type=payload["question_type"],
                        is_required=payload.get("is_required", False),
                        order=payload.get("order", 0),
                        config=payload.get("config", {}),
                    )

        return await upsert_question_sync()

    async def delete_screening_question(self, question_id: str) -> None:
        @sync_to_async
        def delete_question_sync():
            with transaction.atomic():
                OpportunityQuestion.objects.filter(id=question_id).delete()

        await delete_question_sync()

    async def submit_answers(self, application_id: str, answers_payload: List[Dict[str, Any]]) -> List[ApplicationAnswer]:
        @sync_to_async
        def submit_answers_sync():
            with transaction.atomic():
                application = Application.objects.get(id=application_id)
                created: List[ApplicationAnswer] = []

                # Map for quick lookup
                q_by_id = {str(q.id): q for q in application.opportunity.questions.all()}

                for ans in answers_payload:
                    qid = str(ans["question_id"]) if "question_id" in ans else None
                    question = q_by_id.get(qid)
                    if not question:
                        # Skip unknown questions silently in PoC
                        continue

                    answer_text = str(ans.get("answer_text", ""))
                    answer_options = ans.get("answer_options", [])

                    is_disq = False
                    cfg = question.config or {}
                    if question.question_type == "boolean":
                        disq_val = cfg.get("disqualify_when")
                        if isinstance(disq_val, bool):
                            is_disq = (ans.get("answer_text") is True) if disq_val else (ans.get("answer_text") is False)
                    elif question.question_type in ("single_choice", "multi_choice"):
                        disq_set = set(cfg.get("disqualify_options", []))
                        provided = set(answer_options) if isinstance(answer_options, list) else {answer_text}
                        is_disq = len(provided & disq_set) > 0
                    elif question.question_type == "number":
                        min_v = cfg.get("min")
                        max_v = cfg.get("max")
                        try:
                            val = float(answer_text) if answer_text != "" else None
                        except ValueError:
                            val = None
                        if val is not None:
                            if min_v is not None and val < float(min_v):
                                is_disq = True
                            if max_v is not None and val > float(max_v):
                                is_disq = True

                    obj, _ = ApplicationAnswer.objects.update_or_create(
                        application=application,
                        question=question,
                        defaults={
                            "answer_text": answer_text,
                            "answer_options": answer_options if isinstance(answer_options, list) else [],
                            "is_disqualifying": is_disq,
                        },
                    )
                    created.append(obj)
                return created

        return await submit_answers_sync()

    async def schedule_interview_minimal(
        self,
        application_id: str,
        round_name: str,
        scheduled_start,
        scheduled_end,
        location_type: str = "virtual",
        location_details: str = "",
    ) -> Interview:
        @sync_to_async
        def schedule_interview_sync():
            with transaction.atomic():
                interview = Interview.objects.create(
                    application_id=application_id,
                    round_name=round_name,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    location_type=location_type,
                    location_details=location_details,
                )
                ApplicationEvent.objects.create(
                    application_id=application_id,
                    event_type="note_added",
                    metadata={"interview": {
                        "round_name": round_name,
                        "scheduled_start": str(scheduled_start),
                        "scheduled_end": str(scheduled_end),
                        "location_type": location_type,
                    }},
                )
                return interview

        return await schedule_interview_sync()
