"""
API endpoints for profiles app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List, Optional
from asgiref.sync import sync_to_async
from apps.profiles.models import Profile
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
    location: Optional[str] = None
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
            return ProfileSchema(
                id=str(profile.id),
                full_name=f"{profile.first_name} {profile.last_name}".strip(),
                email=profile.email,
                first_name=profile.first_name,
                last_name=profile.last_name,
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
            }
        )

        if not created:
            if payload.first_name is not None:
                profile.first_name = payload.first_name
            if payload.last_name is not None:
                profile.last_name = payload.last_name
            profile.save()

        return ProfileSchema(
            id=str(profile.id),
            full_name=f"{profile.first_name} {profile.last_name}".strip(),
            email=profile.email,
            bio=payload.bio,
            location=payload.location,
            skills=payload.skills or [],
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
