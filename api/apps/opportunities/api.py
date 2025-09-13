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
def list_opportunities(request):
    """List all opportunities."""
    opportunities = Opportunity.objects.all().prefetch_related('organisation', 'opportunity_skills__skill', 'opportunity_experiences')
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
def create_opportunity(request, payload: OpportunityCreateSchema):
    """Create a new opportunity."""
    from apps.organisations.models import Organisation
    organisation = Organisation.objects.get(id=payload.organisation_id)

    opportunity = Opportunity.objects.create(
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


@opportunities_router.get("/{opportunity_id}", response=OpportunitySchema, tags=["Opportunities"])
def get_opportunity(request, opportunity_id: str):
    """Get a specific opportunity by ID."""
    opportunity = Opportunity.objects.prefetch_related('organisation', 'opportunity_skills__skill', 'opportunity_experiences').get(id=opportunity_id)
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
