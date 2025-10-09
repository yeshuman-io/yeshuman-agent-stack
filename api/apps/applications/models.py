from django.db import models
from django.utils import timezone
import uuid

from apps.organisations.models import Organisation
from apps.profiles.models import Profile
from apps.opportunities.models import Opportunity
from apps.evaluations.models import Evaluation


class StageTemplate(models.Model):
    """
    Global stage template list (system-wide pipeline).
    Free-form in v1: order is for UI guidance; transitions are not enforced.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)
    is_terminal = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name


class Application(models.Model):
    """
    Candidate application for an opportunity.
    Enforces no re-apply via unique(profile, opportunity).
    """
    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("invited", "Invited"),
        ("in_review", "In Review"),
        ("interview", "Interview"),
        ("offer", "Offer"),
        ("hired", "Hired"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    SOURCE_CHOICES = [
        ("direct", "Direct"),
        ("referral", "Referral"),
        ("internal", "Internal"),
        ("import", "Import"),
        ("agency", "Agency"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="applications")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="applications")
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="applications")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied", db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="direct", db_index=True)

    evaluation = models.ForeignKey(Evaluation, null=True, blank=True, on_delete=models.SET_NULL, related_name="applications")
    evaluation_snapshot = models.JSONField(default=dict, blank=True)

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    current_stage_instance = models.ForeignKey(
        "ApplicationStageInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="current_for_applications",
    )

    class Meta:
        unique_together = [("profile", "opportunity")]
        indexes = [
            models.Index(fields=["organisation", "status"]),
            models.Index(fields=["opportunity", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.profile} → {self.opportunity} ({self.status})"


class ApplicationStageInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="stages")
    stage_template = models.ForeignKey(StageTemplate, on_delete=models.PROTECT, related_name="instances")

    entered_at = models.DateTimeField(auto_now_add=True)
    exited_at = models.DateTimeField(null=True, blank=True)
    entered_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="entered_application_stages"
    )

    def __str__(self) -> str:
        return f"{self.application} @ {self.stage_template.name}"

    @property
    def is_open(self) -> bool:
        return self.exited_at is None

    def close(self) -> None:
        if not self.exited_at:
            self.exited_at = timezone.now()
            self.save(update_fields=["exited_at"])


class ApplicationEvent(models.Model):
    """Immutable audit log of application activity."""
    EVENT_TYPES = [
        ("applied", "Applied"),
        ("stage_changed", "Stage Changed"),
        ("decision_made", "Decision Made"),
        ("withdrawn", "Withdrawn"),
        ("note_added", "Note Added"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="application_events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.application}: {self.event_type}"


class OpportunityQuestion(models.Model):
    QUESTION_TYPES = [
        ("text", "Text"),
        ("boolean", "Boolean"),
        ("single_choice", "Single Choice"),
        ("multi_choice", "Multi Choice"),
        ("number", "Number"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["opportunity", "order", "id"]

    def __str__(self) -> str:
        return f"{self.opportunity}: {self.question_text[:40]}"


class ApplicationAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(OpportunityQuestion, on_delete=models.CASCADE, related_name="answers")
    answer_text = models.TextField(blank=True)  # for text/number (number can be stringified)
    answer_options = models.JSONField(default=list, blank=True)  # for single/multi choice
    is_disqualifying = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("application", "question")]

    def __str__(self) -> str:
        return f"Answer {self.question_id} for {self.application_id}"


class Interview(models.Model):
    LOCATION_CHOICES = [
        ("virtual", "Virtual"),
        ("onsite", "Onsite"),
    ]
    OUTCOME_CHOICES = [
        ("pending", "Pending"),
        ("pass", "Pass"),
        ("fail", "Fail"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    round_name = models.CharField(max_length=100, default="Interview")
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    location_type = models.CharField(max_length=10, choices=LOCATION_CHOICES, default="virtual")
    location_details = models.CharField(max_length=255, blank=True)
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Interview for {self.application_id} - {self.round_name}"
