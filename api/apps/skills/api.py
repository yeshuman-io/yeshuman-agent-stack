"""
API endpoints for skills app using Django Ninja.
"""

from ninja import Router, Schema, Field
from typing import List
from asgiref.sync import sync_to_async
from apps.skills.models import Skill

# Create router for skills endpoints
skills_router = Router()


class SkillSchema(Schema):
    """Schema for Skill model."""
    id: str
    name: str


class SkillCreateSchema(Schema):
    """Schema for creating a Skill."""
    name: str = Field(min_length=1, max_length=255)


@skills_router.get("/", response=List[SkillSchema], tags=["Skills"])
async def list_skills(request):
    """List all skills."""
    @sync_to_async
    def get_skills_sync():
        return list(Skill.objects.all())

    skills = await get_skills_sync()
    return [
        SkillSchema(
            id=str(skill.id),
            name=skill.name
        )
        for skill in skills
    ]


@skills_router.post("/", response={200: SkillSchema, 400: dict}, tags=["Skills"])
async def create_skill(request, payload: SkillCreateSchema):
    """Create a new skill."""
    @sync_to_async
    def create_skill_sync():
        try:
            skill = Skill.objects.create(
                name=payload.name
            )
            return skill, None
        except Exception as e:
            # Handle unique constraint violations
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                return None, "Skill with this name already exists"
            return None, str(e)

    skill, error = await create_skill_sync()
    if error:
        return 400, {"error": error}

    return 200, SkillSchema(
        id=str(skill.id),
        name=skill.name
    )


@skills_router.get("/{skill_id}", response={200: SkillSchema, 404: dict}, tags=["Skills"])
async def get_skill(request, skill_id: str):
    """Get a specific skill by ID."""
    @sync_to_async
    def get_skill_sync():
        try:
            skill = Skill.objects.get(id=skill_id)
            return skill, None
        except Skill.DoesNotExist:
            return None, "Skill not found"

    skill, error = await get_skill_sync()
    if error:
        return 404, {"error": error}

    return 200, SkillSchema(
        id=str(skill.id),
        name=skill.name
    )
