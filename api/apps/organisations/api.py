"""
API endpoints for organisations app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List
from datetime import datetime
from asgiref.sync import sync_to_async
from apps.organisations.models import Organisation
from apps.opportunities.models import Opportunity, OpportunitySkill, OpportunityExperience
from apps.skills.models import Skill
from ninja.errors import HttpError
import jwt
from django.conf import settings

# Create router for organisations endpoints
organisations_router = Router()


async def get_user_from_token(request):
    """Extract and validate JWT token from request."""
    auth_header = request.headers.get('authorization', '')

    if not auth_header.startswith('Bearer '):
        raise HttpError(401, "No token provided")

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = await sync_to_async(User.objects.get)(id=user_id)
            return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
        pass

    raise HttpError(401, "Invalid token")


async def check_employer_permissions(user):
    """Check if user has employer permissions."""
    # Check if user has employer group
    has_employer_group = await sync_to_async(
        lambda: user.groups.filter(name='employer').exists()
    )()

    if not has_employer_group:
        raise HttpError(403, "Employer access required")

    return True


class OrganisationSchema(Schema):
    """Schema for Organisation model."""
    id: str
    name: str
    slug: str
    description: str = ""
    website: str = ""
    industry: str = ""
    created_at: datetime
    updated_at: datetime


class OrganisationCreateSchema(Schema):
    """Schema for creating an Organisation."""
    name: str
    description: str = ""
    website: str = ""
    industry: str = ""


class OrganisationUpdateSchema(Schema):
    """Schema for updating an Organisation."""
    name: str
    description: str = ""
    website: str = ""
    industry: str = ""


class OpportunitySkillSchema(Schema):
    """Schema for OpportunitySkill in organisation context."""
    id: str
    skill_name: str
    requirement_type: str


class OpportunityExperienceSchema(Schema):
    """Schema for OpportunityExperience in organisation context."""
    id: str
    description: str


class OrganisationOpportunitySchema(Schema):
    """Schema for Opportunity in organisation context."""
    id: str
    title: str
    description: str
    skills: List[OpportunitySkillSchema]
    experiences: List[OpportunityExperienceSchema]
    created_at: datetime
    updated_at: datetime


class OrganisationOpportunitySkillSchema(Schema):
    """Schema for OpportunitySkill in organisation context."""
    skill_id: str
    requirement_type: str  # 'required' or 'preferred'


class OrganisationOpportunityCreateSchema(Schema):
    """Schema for creating an Opportunity for an Organisation."""
    title: str
    description: str
    skills: List[OrganisationOpportunitySkillSchema] = []


class OrganisationOpportunityUpdateSchema(Schema):
    """Schema for updating an Opportunity for an Organisation."""
    title: str
    description: str


@organisations_router.get("/", response=List[OrganisationSchema], tags=["Organisations"])
async def list_organisations(request):
    """List all organisations."""
    @sync_to_async
    def get_organisations_sync():
        return list(Organisation.objects.all())

    organisations = await get_organisations_sync()
    return [
        OrganisationSchema(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            website=org.website,
            industry=org.industry,
            created_at=org.created_at,
            updated_at=org.updated_at
        )
        for org in organisations
    ]


@organisations_router.post("/", response=OrganisationSchema, tags=["Organisations"])
async def create_organisation(request, payload: OrganisationCreateSchema):
    """Create a new organisation."""
    @sync_to_async
    def create_organisation_sync():
        return Organisation.objects.create(
            name=payload.name,
            description=payload.description,
            website=payload.website,
            industry=payload.industry
        )

    organisation = await create_organisation_sync()
    return OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name,
        slug=organisation.slug,
        description=organisation.description,
        website=organisation.website,
        industry=organisation.industry,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at
    )



# Employer-focused organisation endpoints (integrated into main router)

@organisations_router.get("/managed", response=List[OrganisationSchema], tags=["Organisations"])
async def list_managed_organisations(request):
    """List organisations managed by the authenticated employer user."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def get_user_organisations_sync():
        return list(user.managed_organisations.all())

    organisations = await get_user_organisations_sync()
    return [
        OrganisationSchema(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            website=org.website,
            industry=org.industry,
            created_at=org.created_at,
            updated_at=org.updated_at
        )
        for org in organisations
    ]


@organisations_router.post("/managed", response=OrganisationSchema, tags=["Organisations"])
async def create_managed_organisation(request, payload: OrganisationCreateSchema):
    """Create a new organisation and assign it to the authenticated employer user."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def create_organisation_sync():
        org = Organisation.objects.create(
            name=payload.name,
            description=payload.description,
            website=payload.website,
            industry=payload.industry
        )
        # Add the user as a manager of this organisation
        user.managed_organisations.add(org)
        return org

    organisation = await create_organisation_sync()
    return OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name,
        slug=organisation.slug,
        description=organisation.description,
        website=organisation.website,
        industry=organisation.industry,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at
    )


@organisations_router.get("/managed/{organisation_slug}", response=OrganisationSchema, tags=["Organisations"])
async def get_managed_organisation(request, organisation_slug: str):
    """Get a specific organisation by slug (must be managed by the authenticated employer user)."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def get_organisation_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            return org, None
        except Organisation.DoesNotExist:
            return None, "Organisation not found or access denied"

    organisation, error = await get_organisation_sync()
    if error:
        raise HttpError(404, error)

    return OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name,
        slug=organisation.slug,
        description=organisation.description,
        website=organisation.website,
        industry=organisation.industry,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at
    )


@organisations_router.put("/managed/{organisation_slug}", response=OrganisationSchema, tags=["Organisations"])
async def update_managed_organisation(request, organisation_slug: str, payload: OrganisationUpdateSchema):
    """Update a specific organisation by slug (must be managed by the authenticated employer user)."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def update_organisation_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            org.name = payload.name
            org.description = payload.description
            org.website = payload.website
            org.industry = payload.industry
            org.save()
            return org, None
        except Organisation.DoesNotExist:
            return None, "Organisation not found or access denied"

    organisation, error = await update_organisation_sync()
    if error:
        raise HttpError(404, error)

    return OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name,
        slug=organisation.slug,
        description=organisation.description,
        website=organisation.website,
        industry=organisation.industry,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at
    )


@organisations_router.delete("/managed/{organisation_slug}", response=dict, tags=["Organisations"])
async def delete_managed_organisation(request, organisation_slug: str):
    """Delete a specific organisation by slug (must be managed by the authenticated employer user)."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def delete_organisation_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            org.delete()
            return True, None
        except Organisation.DoesNotExist:
            return False, "Organisation not found or access denied"

    success, error = await delete_organisation_sync()
    if error:
        raise HttpError(404, error)

    return {"success": True, "message": "Organisation deleted successfully"}


# Opportunity management endpoints for organisations

@organisations_router.get("/managed/{organisation_slug}/opportunities", response=List[OrganisationOpportunitySchema], tags=["Organisations"])
async def list_organisation_opportunities(request, organisation_slug: str):
    """List opportunities for a managed organisation."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def get_opportunities_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            opportunities = list(org.opportunities.all().prefetch_related('opportunity_skills__skill', 'opportunity_experiences'))
            return opportunities, None
        except Organisation.DoesNotExist:
            return None, "Organisation not found or access denied"

    opportunities, error = await get_opportunities_sync()
    if error:
        raise HttpError(404, error)

    @sync_to_async
    def build_response_data():
        return [
            OrganisationOpportunitySchema(
                id=str(opp.id),
                title=opp.title,
                description=opp.description,
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
                ],
                created_at=opp.created_at,
                updated_at=opp.updated_at
            )
            for opp in opportunities
        ]

    return await build_response_data()


@organisations_router.post("/managed/{organisation_slug}/opportunities", response=OrganisationOpportunitySchema, tags=["Organisations"])
async def create_organisation_opportunity(request, organisation_slug: str, payload: OrganisationOpportunityCreateSchema):
    """Create a new opportunity for a managed organisation."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def create_opportunity_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            opportunity = Opportunity.objects.create(
                title=payload.title,
                description=payload.description,
                organisation=org
            )

            # Create opportunity skills
            for skill_data in payload.skills:
                try:
                    skill = Skill.objects.get(id=skill_data.skill_id)
                    OpportunitySkill.objects.create(
                        opportunity=opportunity,
                        skill=skill,
                        requirement_type=skill_data.requirement_type
                    )
                except Skill.DoesNotExist:
                    # Skip invalid skill IDs
                    pass

            return opportunity, None
        except Organisation.DoesNotExist:
            return None, "Organisation not found or access denied"

    opportunity, error = await create_opportunity_sync()
    if error:
        raise HttpError(404, error)

    @sync_to_async
    def get_opportunity_skills():
        return list(opportunity.opportunity_skills.select_related('skill').all())

    skills_data = await get_opportunity_skills()

    return OrganisationOpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        skills=[
            OpportunitySkillSchema(
                id=str(skill.id),
                skill_name=skill.skill.name,
                requirement_type=skill.requirement_type
            )
            for skill in skills_data
        ],
        experiences=[],
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at
    )


@organisations_router.get("/managed/{organisation_slug}/opportunities/{opportunity_id}", response=OrganisationOpportunitySchema, tags=["Organisations"])
async def get_organisation_opportunity(request, organisation_slug: str, opportunity_id: str):
    """Get a specific opportunity for a managed organisation."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def get_opportunity_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            opportunity = org.opportunities.prefetch_related('opportunity_skills__skill', 'opportunity_experiences').get(id=opportunity_id)
            return opportunity, None
        except (Organisation.DoesNotExist, Opportunity.DoesNotExist):
            return None, "Organisation or opportunity not found or access denied"

    opportunity, error = await get_opportunity_sync()
    if error:
        raise HttpError(404, error)

    @sync_to_async
    def get_opportunity_data():
        skills = list(opportunity.opportunity_skills.select_related('skill').all())
        experiences = list(opportunity.opportunity_experiences.all())
        return skills, experiences

    skills_data, experiences_data = await get_opportunity_data()

    return OrganisationOpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        skills=[
            OpportunitySkillSchema(
                id=str(skill.id),
                skill_name=skill.skill.name,
                requirement_type=skill.requirement_type
            )
            for skill in skills_data
        ],
        experiences=[
            OpportunityExperienceSchema(
                id=str(exp.id),
                description=exp.description
            )
            for exp in experiences_data
        ],
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at
    )


@organisations_router.put("/managed/{organisation_slug}/opportunities/{opportunity_id}", response=OrganisationOpportunitySchema, tags=["Organisations"])
async def update_organisation_opportunity(request, organisation_slug: str, opportunity_id: str, payload: OrganisationOpportunityUpdateSchema):
    """Update a specific opportunity for a managed organisation."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def update_opportunity_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            opportunity = org.opportunities.get(id=opportunity_id)
            opportunity.title = payload.title
            opportunity.description = payload.description
            opportunity.save()
            return opportunity, None
        except (Organisation.DoesNotExist, Opportunity.DoesNotExist):
            return None, "Organisation or opportunity not found or access denied"

    opportunity, error = await update_opportunity_sync()
    if error:
        raise HttpError(404, error)

    @sync_to_async
    def get_opportunity_data():
        skills = list(opportunity.opportunity_skills.select_related('skill').all())
        experiences = list(opportunity.opportunity_experiences.all())
        return skills, experiences

    skills_data, experiences_data = await get_opportunity_data()

    return OrganisationOpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        skills=[
            OpportunitySkillSchema(
                id=str(skill.id),
                skill_name=skill.skill.name,
                requirement_type=skill.requirement_type
            )
            for skill in skills_data
        ],
        experiences=[
            OpportunityExperienceSchema(
                id=str(exp.id),
                description=exp.description
            )
            for exp in experiences_data
        ],
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at
    )


@organisations_router.delete("/managed/{organisation_slug}/opportunities/{opportunity_id}", response=dict, tags=["Organisations"])
async def delete_organisation_opportunity(request, organisation_slug: str, opportunity_id: str):
    """Delete a specific opportunity for a managed organisation."""
    user = await get_user_from_token(request)
    await check_employer_permissions(user)

    @sync_to_async
    def delete_opportunity_sync():
        try:
            org = user.managed_organisations.get(slug=organisation_slug)
            opportunity = org.opportunities.get(id=opportunity_id)
            opportunity.delete()
            return True, None
        except (Organisation.DoesNotExist, Opportunity.DoesNotExist):
            return False, "Organisation or opportunity not found or access denied"

    success, error = await delete_opportunity_sync()
    if error:
        raise HttpError(404, error)

    return {"success": True, "message": "Opportunity deleted successfully"}


@organisations_router.get("/{organisation_id}", response={200: OrganisationSchema, 404: dict}, tags=["Organisations"])
async def get_organisation(request, organisation_id: str):
    """Get a specific organisation by ID."""
    @sync_to_async
    def get_organisation_sync():
        try:
            organisation = Organisation.objects.get(id=organisation_id)
            return organisation, None
        except Organisation.DoesNotExist:
            return None, "Organisation not found"

    organisation, error = await get_organisation_sync()
    if error:
        return 404, {"error": error}

    return 200, OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name,
        slug=organisation.slug,
        description=organisation.description,
        website=organisation.website,
        industry=organisation.industry,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at
    )
