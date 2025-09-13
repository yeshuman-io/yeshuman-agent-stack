"""
API endpoints for profiles app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List
from asgiref.sync import sync_to_async
from apps.profiles.models import Profile

# Create router for profiles endpoints
profiles_router = Router()


class ProfileSchema(Schema):
    """Schema for Profile model."""
    id: str
    first_name: str
    last_name: str
    email: str


class ProfileCreateSchema(Schema):
    """Schema for creating a Profile."""
    first_name: str
    last_name: str
    email: str


@profiles_router.get("/", response=List[ProfileSchema], tags=["Profiles"])
async def list_profiles(request):
    """List all profiles."""
    @sync_to_async
    def get_profiles_sync():
        return list(Profile.objects.all())

    profiles = await get_profiles_sync()
    return [
        ProfileSchema(
            id=str(profile.id),
            first_name=profile.first_name,
            last_name=profile.last_name,
            email=profile.email
        )
        for profile in profiles
    ]


@profiles_router.post("/", response=ProfileSchema, tags=["Profiles"])
async def create_profile(request, payload: ProfileCreateSchema):
    """Create a new profile."""
    @sync_to_async
    def create_profile_sync():
        return Profile.objects.create(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email
        )

    profile = await create_profile_sync()
    return ProfileSchema(
        id=str(profile.id),
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email
    )


@profiles_router.get("/{profile_id}", response={200: ProfileSchema, 404: dict}, tags=["Profiles"])
async def get_profile(request, profile_id: str):
    """Get a specific profile by ID."""
    @sync_to_async
    def get_profile_sync():
        try:
            profile = Profile.objects.get(id=profile_id)
            return profile, None
        except Profile.DoesNotExist:
            return None, "Profile not found"

    profile, error = await get_profile_sync()
    if error:
        return 404, {"error": error}

    return 200, ProfileSchema(
        id=str(profile.id),
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email
    )
