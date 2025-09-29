"""
API endpoints for profiles app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List, Optional
from asgiref.sync import sync_to_async
from apps.profiles.models import Profile, ProfileSkill
from apps.skills.models import Skill
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

# JWT settings (same as accounts API)
JWT_SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = 'HS256'

# Create router for profiles endpoints
profiles_router = Router()


class ProfileSchema(Schema):
    """Schema for Profile model."""
    id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    skills: Optional[List[str]] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ProfileCreateSchema(Schema):
    """Schema for creating a Profile."""
    first_name: str
    last_name: str
    email: str


@profiles_router.get("/my", response={200: ProfileSchema, 401: dict}, tags=["Profiles"])
async def get_my_profile(request):
    """Get current user's profile."""
    # Extract and validate JWT token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return 401, {"error": "No token provided"}

    token = auth_header.split(' ')[1]

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        User = get_user_model()
        user = await sync_to_async(User.objects.get)(id=payload['user_id'])
    except jwt.ExpiredSignatureError:
        return 401, {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return 401, {"error": "Invalid token"}
    except User.DoesNotExist:
        return 401, {"error": "User not found"}

    # Set request.user for session functions
    request.user = user

    @sync_to_async
    def get_profile_sync():
        try:
            profile = Profile.objects.get(email=user.email)
            # Get skills from ProfileSkill relationships
            skills = list(profile.profile_skills.values_list('skill__name', flat=True))
            return ProfileSchema(
                id=str(profile.id),
                full_name=f"{profile.first_name} {profile.last_name}".strip(),
                email=profile.email,
                bio=profile.bio,
                city=profile.city,
                country=profile.country,
                first_name=profile.first_name,
                last_name=profile.last_name,
                skills=skills,
            ), None
        except Profile.DoesNotExist:
            # Return profile data from user model if no profile exists
            return ProfileSchema(
                full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                skills=[],
            ), None

    profile_data, error = await get_profile_sync()
    return profile_data


@profiles_router.post("/my", response=ProfileSchema, tags=["Profiles"])
async def update_my_profile(request, payload: ProfileSchema):
    """Update current user's profile."""
    # Extract and validate JWT token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return 401, {"error": "No token provided"}

    token = auth_header.split(' ')[1]

    try:
        jwt_payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        User = get_user_model()
        user = await sync_to_async(User.objects.get)(id=jwt_payload['user_id'])
    except jwt.ExpiredSignatureError:
        return 401, {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return 401, {"error": "Invalid token"}
    except User.DoesNotExist:
        return 401, {"error": "User not found"}

    # Set request.user for session functions
    request.user = user

    @sync_to_async
    def update_profile_sync():
        profile, created = Profile.objects.get_or_create(
            email=user.email,
            defaults={
                'first_name': payload.first_name or user.first_name or '',
                'last_name': payload.last_name or user.last_name or '',
                'bio': payload.bio,
                'city': payload.city,
                'country': payload.country,
            }
        )

        if not created:
            # Update existing profile
            if payload.first_name is not None:
                profile.first_name = payload.first_name
            if payload.last_name is not None:
                profile.last_name = payload.last_name
            if payload.bio is not None:
                profile.bio = payload.bio
            if payload.city is not None:
                profile.city = payload.city
            if payload.country is not None:
                profile.country = payload.country
            profile.save()

        # Handle skills
        if payload.skills is not None:
            current_skills = set(profile.profile_skills.values_list('skill__name', flat=True))
            new_skills = set(payload.skills)

            # Skills to add
            skills_to_add = new_skills - current_skills
            for skill_name in skills_to_add:
                skill, _ = Skill.objects.get_or_create(name=skill_name)
                ProfileSkill.objects.get_or_create(
                    profile=profile,
                    skill=skill,
                    defaults={'evidence_level': 'stated'}
                )

            # Skills to remove
            skills_to_remove = current_skills - new_skills
            for skill_name in skills_to_remove:
                try:
                    skill = Skill.objects.get(name=skill_name)
                    ProfileSkill.objects.filter(profile=profile, skill=skill).delete()
                except Skill.DoesNotExist:
                    pass  # Skill doesn't exist, nothing to remove

        # Get updated skills list
        skills = list(profile.profile_skills.values_list('skill__name', flat=True))

        return ProfileSchema(
            id=str(profile.id),
            full_name=f"{profile.first_name} {profile.last_name}".strip(),
            email=profile.email,
            bio=profile.bio,
            city=profile.city,
            country=profile.country,
            skills=skills,
            first_name=profile.first_name,
            last_name=profile.last_name,
        )

    profile_data = await update_profile_sync()
    return profile_data


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
