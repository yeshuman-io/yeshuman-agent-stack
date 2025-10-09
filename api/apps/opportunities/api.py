"""
API endpoints for opportunities app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List
from apps.opportunities.models import Opportunity, OpportunitySkill, OpportunityExperience

# Create router for opportunities endpoints
opportunities_router = Router()


class OpportunitySkillSchema(Schema):
    """Schema for OpportunitySkill model."""
    id: str
    skill_name: str
    requirement_type: str


class OpportunityExperienceSchema(Schema):
    """Schema for OpportunityExperience model."""
    id: str
    description: str


class OpportunitySchema(Schema):
    """Schema for Opportunity model."""
    id: str
    title: str
    description: str
    organisation_name: str
    skills: List[OpportunitySkillSchema]
    experiences: List[OpportunityExperienceSchema]


class OpportunityCreateSchema(Schema):
    """Schema for creating an Opportunity."""
    title: str
    description: str
    organisation_id: str


@opportunities_router.get("/", response=List[OpportunitySchema], tags=["Opportunities"])
async def list_opportunities(request):
    """List all opportunities."""
    from asgiref.sync import sync_to_async

    opportunities = await sync_to_async(list)(Opportunity.objects.all().prefetch_related('organisation', 'opportunity_skills__skill', 'opportunity_experiences'))
    return [
        OpportunitySchema(
            id=str(opp.id),
            title=opp.title,
            description=opp.description,
            organisation_name=opp.organisation.name,
            skills=[
                OpportunitySkillSchema(
                    id=str(skill.id),
                    skill_name=skill.skill.name,
                    requirement_type=skill.requirement_type
                )
                for skill in opp.opportunity_skills.all()
            ],
            experiences=[
                OpportunityExperienceSchema(
                    id=str(exp.id),
                    description=exp.description
                )
                for exp in opp.opportunity_experiences.all()
            ]
        )
        for opp in opportunities
    ]


@opportunities_router.post("/", response=OpportunitySchema, tags=["Opportunities"])
async def create_opportunity(request, payload: OpportunityCreateSchema):
    """Create a new opportunity."""
    from asgiref.sync import sync_to_async
    from apps.organisations.models import Organisation

    organisation = await sync_to_async(Organisation.objects.get)(id=payload.organisation_id)

    opportunity = await sync_to_async(Opportunity.objects.create)(
        title=payload.title,
        description=payload.description,
        organisation=organisation
    )
    return OpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        organisation_name=opportunity.organisation.name,
        skills=[],
        experiences=[]
    )


@opportunities_router.get("/{opportunity_id}/questions", response=List[dict], tags=["Opportunities"])
async def get_opportunity_questions(request, opportunity_id: str):
    """Get screening questions for an opportunity."""
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_questions_sync():
        try:
            opportunity = Opportunity.objects.get(id=opportunity_id)
            questions = opportunity.questions.all().order_by('order')
            return list(questions)
        except Opportunity.DoesNotExist:
            return None

    questions = await get_questions_sync()
    if questions is None:
        return []

    return [
        {
            'id': str(q.id),
            'question_text': q.question_text,
            'question_type': q.question_type,
            'is_required': q.is_required,
            'order': q.order,
            'config': q.config
        }
        for q in questions
    ]


@opportunities_router.get("/{opportunity_id}", response=OpportunitySchema, tags=["Opportunities"])
async def get_opportunity(request, opportunity_id: str):
    """Get a specific opportunity by ID."""
    from asgiref.sync import sync_to_async

    opportunity = await sync_to_async(Opportunity.objects.prefetch_related('organisation', 'opportunity_skills__skill', 'opportunity_experiences').get)(id=opportunity_id)
    return OpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        organisation_name=opportunity.organisation.name,
        skills=[
            OpportunitySkillSchema(
                id=str(skill.id),
                skill_name=skill.skill.name,
                requirement_type=skill.requirement_type
            )
            for skill in opportunity.opportunity_skills.all()
        ],
        experiences=[
            OpportunityExperienceSchema(
                id=str(exp.id),
                description=exp.description
            )
            for exp in opportunity.opportunity_experiences.all()
        ]
    )
