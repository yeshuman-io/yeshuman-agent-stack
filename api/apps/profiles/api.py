"""
API endpoints for profiles app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List, Optional
from asgiref.sync import sync_to_async
from apps.profiles.models import Profile, ProfileSkill, ProfileExperience, ProfileExperienceSkill
from apps.skills.models import Skill
from apps.organisations.models import Organisation
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
    experiences: Optional[List["ExperienceSchema"]] = None


class ExperienceSchema(Schema):
    """Schema for ProfileExperience model (read)."""
    id: str
    title: str
    company: str
    description: Optional[str] = None
    start_date: str  # ISO date string YYYY-MM-DD
    end_date: Optional[str] = None  # ISO date string or None
    skills: List[str] = []  # Skills demonstrated in this experience


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
            profile = Profile.objects.get(user=user)
            # Get skills from ProfileSkill relationships
            skills = list(profile.profile_skills.values_list('skill__name', flat=True))
            # Get experiences (ordered by start_date desc) with skills
            experiences = []
            for exp in profile.profile_experiences.select_related('organisation').prefetch_related('profile_experience_skills__skill').all().order_by('-start_date'):
                exp_skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))
                experiences.append(ExperienceSchema(
                    id=str(exp.id),
                    title=exp.title,
                    company=exp.organisation.name,
                    description=exp.description or None,
                    start_date=exp.start_date.isoformat(),
                    end_date=exp.end_date.isoformat() if exp.end_date else None,
                    skills=exp_skills,
                ))

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
                experiences=experiences,
            ), None
        except Profile.DoesNotExist:
            # Return profile data from user model if no profile exists
            return ProfileSchema(
                full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                skills=[],
                experiences=[],
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
            user=user,
            defaults={
                'email': user.email,
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

        # Get updated experiences list with skills
        experiences = []
        for exp in profile.profile_experiences.select_related('organisation').prefetch_related('profile_experience_skills__skill').all().order_by('-start_date'):
            exp_skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))
            experiences.append(ExperienceSchema(
                id=str(exp.id),
                title=exp.title,
                company=exp.organisation.name,
                description=exp.description or None,
                start_date=exp.start_date.isoformat(),
                end_date=exp.end_date.isoformat() if exp.end_date else None,
                skills=exp_skills,
            ))

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
            experiences=experiences,
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


# ==============================
# Experiences CRUD (current user)
# ==============================

class ExperienceCreateSchema(Schema):
    title: str
    company: str
    start_date: str
    description: Optional[str] = None
    end_date: Optional[str] = None


class ExperienceUpdateSchema(Schema):
    title: Optional[str] = None
    company: Optional[str] = None
    start_date: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[str] = None


def _parse_iso_date(value: Optional[str]):
    from datetime import datetime
    if value is None:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        return None


@profiles_router.get("/my/experiences", response={200: List[ExperienceSchema], 401: dict}, tags=["Profiles"])
async def list_my_experiences(request):
    """List current user's experiences."""
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

    @sync_to_async
    def fetch_experiences():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return []
        items = []
        for exp in profile.profile_experiences.select_related('organisation').prefetch_related('profile_experience_skills__skill').all().order_by('-start_date'):
            exp_skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))
            items.append(ExperienceSchema(
                id=str(exp.id),
                title=exp.title,
                company=exp.organisation.name,
                description=exp.description or None,
                start_date=exp.start_date.isoformat(),
                end_date=exp.end_date.isoformat() if exp.end_date else None,
                skills=exp_skills,
            ))
        return items

    items = await fetch_experiences()
    return items


@profiles_router.post("/my/experiences", response={201: ExperienceSchema, 400: dict, 401: dict}, tags=["Profiles"])
async def create_my_experience(request, payload: ExperienceCreateSchema):
    """Create a new experience for the current user."""
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

    @sync_to_async
    def create_exp_sync():
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={'email': user.email, 'first_name': user.first_name or '', 'last_name': user.last_name or ''}
        )

        start_date = _parse_iso_date(payload.start_date)
        end_date = _parse_iso_date(payload.end_date)
        if start_date is None:
            raise ValueError('Invalid start_date')

        organisation, _ = Organisation.objects.get_or_create(name=payload.company)

        exp = ProfileExperience.objects.create(
            profile=profile,
            organisation=organisation,
            title=payload.title,
            description=payload.description or '',
            start_date=start_date,
            end_date=end_date
        )
        # Optional: generate embedding now
        try:
            exp.ensure_embedding()
        except Exception:
            pass

        return ExperienceSchema(
            id=str(exp.id),
            title=exp.title,
            company=organisation.name,
            description=exp.description or None,
            start_date=exp.start_date.isoformat(),
            end_date=exp.end_date.isoformat() if exp.end_date else None,
            skills=[],  # New experience starts with no skills
        )

    try:
        result = await create_exp_sync()
        return 201, result
    except ValueError as ve:
        return 400, {"error": str(ve)}


@profiles_router.patch("/my/experiences/{experience_id}", response={200: ExperienceSchema, 400: dict, 401: dict, 404: dict}, tags=["Profiles"])
async def update_my_experience(request, experience_id: str, payload: ExperienceUpdateSchema):
    """Update an existing experience for the current user."""
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

    @sync_to_async
    def update_exp_sync():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return None, 404, {"error": "Profile not found"}

        try:
            exp = ProfileExperience.objects.select_related('organisation', 'profile').get(id=experience_id, profile=profile)
        except ProfileExperience.DoesNotExist:
            return None, 404, {"error": "Experience not found"}

        changed = False

        if payload.title is not None:
            exp.title = payload.title
            changed = True
        if payload.description is not None:
            exp.description = payload.description or ''
            changed = True
        if payload.start_date is not None:
            sd = _parse_iso_date(payload.start_date)
            if sd is None:
                return None, 400, {"error": "Invalid start_date"}
            exp.start_date = sd
            changed = True
        if payload.end_date is not None:
            ed = _parse_iso_date(payload.end_date)
            # Allow clearing end_date with None or empty string
            exp.end_date = ed
            changed = True
        if payload.company is not None:
            org, _ = Organisation.objects.get_or_create(name=payload.company)
            exp.organisation = org
            changed = True

        if changed:
            exp.save()
            try:
                exp.ensure_embedding()
            except Exception:
                pass

        # Get updated skills for the experience
        exp_skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))

        return ExperienceSchema(
            id=str(exp.id),
            title=exp.title,
            company=exp.organisation.name,
            description=exp.description or None,
            start_date=exp.start_date.isoformat(),
            end_date=exp.end_date.isoformat() if exp.end_date else None,
            skills=exp_skills,
        ), 200, None

    result, status_code, error = await update_exp_sync()
    if error:
        return status_code, error
    return result


@profiles_router.delete("/my/experiences/{experience_id}", response={204: None, 401: dict, 404: dict}, tags=["Profiles"])
async def delete_my_experience(request, experience_id: str):
    """Delete an experience for the current user."""
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

    @sync_to_async
    def delete_exp_sync():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return 404, {"error": "Profile not found"}

        try:
            exp = ProfileExperience.objects.get(id=experience_id, profile=profile)
        except ProfileExperience.DoesNotExist:
            return 404, {"error": "Experience not found"}

        exp.delete()
        return 204, None

    status_code, error = await delete_exp_sync()
    if error:
        return status_code, error
    return 204, None


# ==============================
# Experience Skills Management
# ==============================

class ExperienceSkillCreateSchema(Schema):
    skill_names: List[str]  # List of skill names to add


@profiles_router.get("/my/experiences/{experience_id}/skills", response={200: List[str], 401: dict, 404: dict}, tags=["Profiles"])
async def list_experience_skills(request, experience_id: str):
    """List skills for a specific experience."""
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

    @sync_to_async
    def get_skills():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return None, 404, {"error": "Profile not found"}

        try:
            exp = ProfileExperience.objects.select_related('profile').get(id=experience_id, profile=profile)
        except ProfileExperience.DoesNotExist:
            return None, 404, {"error": "Experience not found"}

        skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))
        return skills, 200, None

    result, status_code, error = await get_skills()
    if error:
        return status_code, error
    return result


@profiles_router.post("/my/experiences/{experience_id}/skills", response={200: ExperienceSchema, 400: dict, 401: dict, 404: dict}, tags=["Profiles"])
async def add_experience_skills(request, experience_id: str, payload: ExperienceSkillCreateSchema):
    """Add skills to a specific experience."""
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

    @sync_to_async
    def add_skills_sync():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return None, 404, {"error": "Profile not found"}

        try:
            exp = ProfileExperience.objects.select_related('organisation').prefetch_related('profile_experience_skills__skill').get(id=experience_id, profile=profile)
        except ProfileExperience.DoesNotExist:
            return None, 404, {"error": "Experience not found"}

        added_skills = []
        for skill_name in payload.skill_names:
            # Get or create the skill
            skill, _ = Skill.objects.get_or_create(name=skill_name)

            # Create ProfileExperienceSkill if it doesn't exist
            exp_skill, created = ProfileExperienceSkill.objects.get_or_create(
                profile_experience=exp,
                skill=skill,
                defaults={}
            )

            if created:
                # Generate embedding for the new experience-skill relationship
                try:
                    exp_skill.ensure_embedding()
                except Exception:
                    pass

                added_skills.append(skill_name)

                # Also ensure ProfileSkill exists with experienced evidence level
                profile_skill, _ = ProfileSkill.objects.get_or_create(
                    profile=profile,
                    skill=skill,
                    defaults={'evidence_level': 'experienced'}
                )
                # Update to experienced if it was only stated
                if profile_skill.evidence_level == 'stated':
                    profile_skill.evidence_level = 'experienced'
                    profile_skill.save(update_fields=['evidence_level'])
                    try:
                        profile_skill.ensure_embedding()
                    except Exception:
                        pass

        # Return updated experience with all skills
        exp_skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))
        return ExperienceSchema(
            id=str(exp.id),
            title=exp.title,
            company=exp.organisation.name,
            description=exp.description or None,
            start_date=exp.start_date.isoformat(),
            end_date=exp.end_date.isoformat() if exp.end_date else None,
            skills=exp_skills,
        ), 200, None

    result, status_code, error = await add_skills_sync()
    if error:
        return status_code, error
    return result


@profiles_router.delete("/my/experiences/{experience_id}/skills/{skill_name}", response={200: ExperienceSchema, 401: dict, 404: dict}, tags=["Profiles"])
async def remove_experience_skill(request, experience_id: str, skill_name: str):
    """Remove a skill from a specific experience."""
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

    @sync_to_async
    def remove_skill_sync():
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return None, 404, {"error": "Profile not found"}

        try:
            exp = ProfileExperience.objects.select_related('organisation').prefetch_related('profile_experience_skills__skill').get(id=experience_id, profile=profile)
        except ProfileExperience.DoesNotExist:
            return None, 404, {"error": "Experience not found"}

        try:
            skill = Skill.objects.get(name=skill_name)
        except Skill.DoesNotExist:
            return None, 404, {"error": "Skill not found"}

        # Remove the ProfileExperienceSkill relationship
        deleted_count, _ = ProfileExperienceSkill.objects.filter(
            profile_experience=exp,
            skill=skill
        ).delete()

        if deleted_count == 0:
            return None, 404, {"error": "Skill not associated with this experience"}

        # Return updated experience with remaining skills
        exp_skills = list(exp.profile_experience_skills.values_list('skill__name', flat=True))
        return ExperienceSchema(
            id=str(exp.id),
            title=exp.title,
            company=exp.organisation.name,
            description=exp.description or None,
            start_date=exp.start_date.isoformat(),
            end_date=exp.end_date.isoformat() if exp.end_date else None,
            skills=exp_skills,
        ), 200, None

    result, status_code, error = await remove_skill_sync()
    if error:
        return status_code, error
    return result
