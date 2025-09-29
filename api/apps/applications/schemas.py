"""
Pydantic schemas for applications app.
Separated from api.py for better organization.
"""

from ninja import Schema
from typing import List, Optional



# =====================================================
# APPLICATION SCHEMAS
# =====================================================

class ApplicationStageSchema(Schema):
    """Schema for ApplicationStageInstance model."""
    id: str
    stage_name: str
    entered_at: str
    is_open: bool


class ApplicationSchema(Schema):
    """Schema for Application model."""
    id: str
    profile_id: str
    opportunity_title: str
    organisation_name: str
    status: str
    source: str
    applied_at: str
    current_stage: Optional[ApplicationStageSchema]


class ApplicationCreateSchema(Schema):
    """Schema for creating an Application."""
    profile_id: str
    opportunity_id: str
    organisation_id: str
    source: str = "direct"


# =====================================================
# STAGE MANAGEMENT SCHEMAS
# =====================================================

class StageTemplateSchema(Schema):
    """Schema for StageTemplate model."""
    id: str
    name: str
    slug: str
    order: int
    is_terminal: bool


class StageChangeSchema(Schema):
    """Schema for changing application stage."""
    stage_slug: str
    actor_id: Optional[int] = None


# =====================================================
# APPLICATION ACTION SCHEMAS
# =====================================================

class ApplicationActionSchema(Schema):
    """Schema for application actions."""
    reason: Optional[str] = None


class DecisionSchema(Schema):
    """Schema for recording decisions."""
    status: str
    reason: Optional[str] = None


# =====================================================
# EVENT SCHEMAS
# =====================================================

class ApplicationEventSchema(Schema):
    """Schema for ApplicationEvent model."""
    id: str
    event_type: str
    metadata: dict
    created_at: str
    actor_id: Optional[int]


# =====================================================
# SCREENING SCHEMAS
# =====================================================

class OpportunityQuestionSchema(Schema):
    """Schema for OpportunityQuestion model."""
    id: str
    question_text: str
    question_type: str
    is_required: bool
    order: int
    config: dict


class ApplicationAnswerSchema(Schema):
    """Schema for ApplicationAnswer model."""
    id: str
    question_id: str
    answer_text: str
    answer_options: List[str]
    is_disqualifying: bool


class ScreeningAnswersSchema(Schema):
    """Schema for submitting screening answers."""
    answers: List[dict]


# =====================================================
# INTERVIEW SCHEMAS
# =====================================================

class InterviewSchema(Schema):
    """Schema for Interview model."""
    id: str
    round_name: str
    scheduled_start: str
    scheduled_end: str
    location_type: str
    location_details: str
    outcome: str


class InterviewCreateSchema(Schema):
    """Schema for creating an interview."""
    round_name: str
    scheduled_start: str
    scheduled_end: str
    location_type: str = "virtual"
    location_details: str = ""


# =====================================================
# EXPORT ALL SCHEMAS
# =====================================================

__all__ = [
    # Application schemas
    'ApplicationStageSchema',
    'ApplicationSchema',
    'ApplicationCreateSchema',

    # Stage management schemas
    'StageTemplateSchema',
    'StageChangeSchema',

    # Application action schemas
    'ApplicationActionSchema',
    'DecisionSchema',

    # Event schemas
    'ApplicationEventSchema',

    # Screening schemas
    'OpportunityQuestionSchema',
    'ApplicationAnswerSchema',
    'ScreeningAnswersSchema',

    # Interview schemas
    'InterviewSchema',
    'InterviewCreateSchema',
]
