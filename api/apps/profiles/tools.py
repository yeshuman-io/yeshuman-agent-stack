"""
Tools for profiles app using LangChain BaseTool.
Provides tools for managing candidate profiles, skills, and experience.
"""

from typing import Optional, List, Dict
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from pydantic import BaseModel, Field
from datetime import datetime, date

# Django imports
from asgiref.sync import sync_to_async

from apps.profiles.models import Profile, ProfileSkill, ProfileExperience
from apps.organisations.models import Organisation
from apps.skills.models import Skill


# =====================================================
# PROFILE MANAGEMENT TOOLS
# =====================================================

class CreateProfileInput(BaseModel):
    """Input for creating a new candidate profile."""
    first_name: str = Field(description="Candidate's first name")
    last_name: str = Field(description="Candidate's last name")
    email: str = Field(description="Candidate's email address")
    skills: Optional[List[str]] = Field(
        default=None,
        description="List of candidate's skills"
    )
    experiences: Optional[List[Dict]] = Field(
        default=None,
        description="List of work experiences with title, company, description, start_date, end_date"
    )


class CreateProfileTool(BaseTool):
    """Create a new candidate profile in the system."""

    name: str = "create_profile"
    description: str = """Create a new candidate profile that can be used for opportunity matching.

    This tool:
    - Creates the profile in the database
    - Sets up skills and experiences if provided
    - Returns the profile ID for use with other tools
    - Enables opportunity matching via find_opportunities_for_profile

    Use this when you need to register a new candidate or when candidate information
    mentioned in conversation doesn't exist in the system yet."""

    args_schema: type[BaseModel] = CreateProfileInput

    def _run(self, first_name: str, last_name: str, email: str, skills: Optional[List[str]] = None,
             experiences: Optional[List[Dict]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the create profile tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                return await self._create_profile_async(first_name, last_name, email, skills, experiences)

            return run_service()

        except Exception as e:
            return f"❌ Failed to create profile: {str(e)}"

    async def _arun(self, first_name: str, last_name: str, email: str, skills: Optional[List[str]] = None,
                   experiences: Optional[List[Dict]] = None, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the create profile tool asynchronously."""
        return await self._create_profile_async(first_name, last_name, email, skills, experiences)

    async def _create_profile_async(self, first_name: str, last_name: str, email: str,
                                   skills: Optional[List[str]] = None, experiences: Optional[List[Dict]] = None) -> str:
        """Internal method to create profile."""
        try:
            # Create the profile
            profile = await sync_to_async(Profile.objects.create)(
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            created_skills = []
            created_experiences = []

            # Add skills if provided
            if skills:
                for skill_name in skills:
                    # Get or create the skill
                    skill, skill_created = await sync_to_async(Skill.objects.get_or_create)(name=skill_name)

                    # Create profile skill relationship
                    profile_skill = await sync_to_async(ProfileSkill.objects.create)(
                        profile=profile,
                        skill=skill,
                        evidence_level='stated'  # Default evidence level
                    )

                    # Generate embedding for new profile skill
                    await sync_to_async(profile_skill.ensure_embedding)()

                    created_skills.append(skill_name)

            # Add experiences if provided
            if experiences:
                for exp_data in experiences:
                    # Get or create the organization
                    company_name = exp_data.get('company', 'Unknown Company')
                    organisation, created = await sync_to_async(Organisation.objects.get_or_create)(name=company_name)

                    # Parse dates
                    start_date = exp_data.get('start_date')
                    end_date = exp_data.get('end_date')

                    if isinstance(start_date, str):
                        try:
                            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                        except:
                            start_date = date(2020, 1, 1)  # Default fallback
                    elif not isinstance(start_date, date):
                        start_date = date(2020, 1, 1)

                    if end_date and isinstance(end_date, str):
                        try:
                            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                        except:
                            end_date = None
                    elif end_date and not isinstance(end_date, date):
                        end_date = None

                    # Create profile experience
                    await sync_to_async(ProfileExperience.objects.create)(
                        profile=profile,
                        organisation=organisation,
                        title=exp_data.get('title', 'Position'),
                        description=exp_data.get('description', ''),
                        start_date=start_date,
                        end_date=end_date
                    )
                    created_experiences.append(f"{exp_data.get('title', 'Position')} at {company_name}")

            # Build response
            skills_summary = f"\n• Skills: {', '.join(created_skills)}" if created_skills else ""
            exp_summary = f"\n• Experiences: {', '.join(created_experiences)}" if created_experiences else ""

            result = f"""✅ Candidate profile created successfully!

👤 Profile Details:
• Name: {first_name} {last_name}
• Email: {email}
• Profile ID: {profile.id}{skills_summary}{exp_summary}

🎯 Next Steps:
You can now use find_opportunities_for_profile with ID: {profile.id}
"""

            return result

        except Exception as e:
            return f"❌ Failed to create profile: {str(e)}"


class UpdateProfileInput(BaseModel):
    """Input for updating an existing candidate profile."""
    profile_id: str = Field(description="UUID of the profile to update")
    first_name: Optional[str] = Field(default=None, description="New first name (optional)")
    last_name: Optional[str] = Field(default=None, description="New last name (optional)")
    email: Optional[str] = Field(default=None, description="New email address (optional)")
    add_skills: Optional[List[str]] = Field(
        default=None,
        description="List of skills to add to the profile"
    )
    remove_skills: Optional[List[str]] = Field(
        default=None,
        description="List of skills to remove from the profile"
    )
    add_experiences: Optional[List[Dict]] = Field(
        default=None,
        description="List of work experiences to add with title, company, description, start_date, end_date"
    )


class UpdateUserProfileInput(BaseModel):
    """Input for updating the current user's profile."""
    user_id: Optional[int] = Field(default=None, description="User ID (automatically provided by agent)")
    first_name: Optional[str] = Field(default=None, description="Update the user's first name")
    last_name: Optional[str] = Field(default=None, description="Update the user's last name")
    bio: Optional[str] = Field(default=None, description="Update the user's bio/description")
    city: Optional[str] = Field(default=None, description="Update the user's city location")
    country: Optional[str] = Field(default=None, description="Update the user's country location")
    add_skills: Optional[List[str]] = Field(
        default=None,
        description="List of new skills to add to the profile"
    )
    remove_skills: Optional[List[str]] = Field(
        default=None,
        description="List of skills to remove from the profile"
    )


class UpdateUserProfileTool(BaseTool):
    """Update the current user's profile with real-time UI feedback."""

    name: str = "update_user_profile"
    description: str = """Update the current user's profile with new information.

This tool updates the authenticated user's profile and provides real-time feedback
to the UI via SSE events. Use this when the user asks you to modify their profile.

Parameters:
- first_name: Update the user's first name
- last_name: Update the user's last name
- bio: Update the user's bio/description
- city: Update the user's city location
- country: Update the user's country location
- add_skills: List of new skills to add to the profile
- remove_skills: List of skills to remove from the profile

The UI will automatically update when this tool completes successfully."""

    args_schema: type[BaseModel] = UpdateUserProfileInput

    def __init__(self, user=None):
        """Initialize with optional user context for agent usage."""
        super().__init__()
        self._user = user

    def _run(self, user_id: Optional[int] = None, first_name: Optional[str] = None, last_name: Optional[str] = None,
             bio: Optional[str] = None, city: Optional[str] = None, country: Optional[str] = None,
             add_skills: Optional[List[str]] = None, remove_skills: Optional[List[str]] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the update user profile tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                return await self._update_user_profile_async(
                    user_id, first_name, last_name, bio, city, country, add_skills, remove_skills
                )

            return run_service()

        except Exception as e:
            return f"❌ Failed to update profile: {str(e)}"

    async def _arun(self, user_id: Optional[int] = None, first_name: Optional[str] = None, last_name: Optional[str] = None,
                   bio: Optional[str] = None, city: Optional[str] = None, country: Optional[str] = None,
                   add_skills: Optional[List[str]] = None, remove_skills: Optional[List[str]] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the update user profile tool asynchronously."""
        return await self._update_user_profile_async(
            user_id, first_name, last_name, bio, city, country, add_skills, remove_skills
        )

    async def _update_user_profile_async(self, user_id: Optional[int] = None, first_name: Optional[str] = None,
                                       last_name: Optional[str] = None, bio: Optional[str] = None,
                                       city: Optional[str] = None, country: Optional[str] = None,
                                       add_skills: Optional[List[str]] = None,
                                       remove_skills: Optional[List[str]] = None) -> str:
        """Internal method to update user profile."""
        try:
            # Get user - either from parameter (agent context) or from request (API context)
            if user_id:
                # Agent context: get user by ID
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = await sync_to_async(User.objects.get)(id=user_id)
            else:
                # API context: get user from request
                from apps.accounts.utils import negotiate_user_focus
                focus_data = await negotiate_user_focus(None)
                user = focus_data.get('user')

            if not user:
                return "❌ Error: No authenticated user found"

            # Get or create profile
            profile, created = await sync_to_async(Profile.objects.get_or_create)(
                email=user.email,
                defaults={
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                }
            )

            updated_fields = []

            # Update basic info
            if first_name is not None:
                profile.first_name = first_name
                updated_fields.append(f"first name")
            if last_name is not None:
                profile.last_name = last_name
                updated_fields.append(f"last name")
            if bio is not None:
                profile.bio = bio
                updated_fields.append(f"bio")
            if city is not None:
                profile.city = city
                updated_fields.append(f"city")
            if country is not None:
                profile.country = country
                updated_fields.append(f"country")

            await sync_to_async(profile.save)()

            # Handle skills
            added_skills = []
            removed_skills = []

            if add_skills:
                for skill_name in add_skills:
                    skill, _ = await sync_to_async(Skill.objects.get_or_create)(name=skill_name)
                    profile_skill, skill_created = await sync_to_async(ProfileSkill.objects.get_or_create)(
                        profile=profile,
                        skill=skill,
                        defaults={'evidence_level': 'stated'}
                    )
                    if skill_created:
                        added_skills.append(skill_name)

            if remove_skills:
                for skill_name in remove_skills:
                    try:
                        skill = await sync_to_async(Skill.objects.get)(name=skill_name)
                        deleted_count, _ = await sync_to_async(
                            ProfileSkill.objects.filter(profile=profile, skill=skill).delete
                        )()
                        if deleted_count > 0:
                            removed_skills.append(skill_name)
                    except Skill.DoesNotExist:
                        pass  # Skill doesn't exist, nothing to remove

            # Build response
            response_parts = ["✅ Your profile has been updated successfully!"]

            if updated_fields:
                response_parts.append(f"\n📝 Updated: {', '.join(updated_fields)}")

            if added_skills:
                response_parts.append(f"\n➕ Added skills: {', '.join(added_skills)}")

            if removed_skills:
                response_parts.append(f"\n➖ Removed skills: {', '.join(removed_skills)}")

            if not (updated_fields or added_skills or removed_skills):
                response_parts.append("\n📋 No changes were made.")

            return ''.join(response_parts)

        except Exception as e:
            return f"❌ Failed to update profile: {str(e)}"


class UpdateProfileTool(BaseTool):
    """Update an existing candidate profile."""

    name: str = "update_profile"
    description: str = """Update an existing candidate profile with new information.

    This tool can:
    - Update basic profile information (name, email)
    - Add new skills to the profile
    - Remove existing skills from the profile
    - Add new work experiences
    - Generate embeddings for any new data

    Use this when you need to modify existing candidate information or add new qualifications."""

    args_schema: type[BaseModel] = UpdateProfileInput

    def _run(self, profile_id: str, first_name: Optional[str] = None, last_name: Optional[str] = None,
             email: Optional[str] = None, add_skills: Optional[List[str]] = None,
             remove_skills: Optional[List[str]] = None, add_experiences: Optional[List[Dict]] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the update profile tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                return await self._update_profile_async(
                    profile_id, first_name, last_name, email, add_skills, remove_skills, add_experiences
                )

            return run_service()

        except Exception as e:
            return f"❌ Failed to update profile: {str(e)}"

    async def _arun(self, profile_id: str, first_name: Optional[str] = None, last_name: Optional[str] = None,
                   email: Optional[str] = None, add_skills: Optional[List[str]] = None,
                   remove_skills: Optional[List[str]] = None, add_experiences: Optional[List[Dict]] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the update profile tool asynchronously."""
        return await self._update_profile_async(
            profile_id, first_name, last_name, email, add_skills, remove_skills, add_experiences
        )

    async def _update_profile_async(self, profile_id: str, first_name: Optional[str] = None,
                                   last_name: Optional[str] = None, email: Optional[str] = None,
                                   add_skills: Optional[List[str]] = None, remove_skills: Optional[List[str]] = None,
                                   add_experiences: Optional[List[Dict]] = None) -> str:
        """Internal method to update profile."""
        try:
            # Get the existing profile
            profile = await sync_to_async(Profile.objects.get)(id=profile_id)

            updated_fields = []

            # Update basic profile information
            profile_updated = False
            if first_name:
                profile.first_name = first_name
                profile_updated = True
                updated_fields.append(f"First name: {first_name}")

            if last_name:
                profile.last_name = last_name
                profile_updated = True
                updated_fields.append(f"Last name: {last_name}")

            if email:
                profile.email = email
                profile_updated = True
                updated_fields.append(f"Email: {email}")

            if profile_updated:
                await sync_to_async(profile.save)()

            # Add new skills
            added_skills = []
            if add_skills:
                for skill_name in add_skills:
                    # Get or create the skill
                    skill, skill_created = await sync_to_async(Skill.objects.get_or_create)(name=skill_name)

                    # Check if skill already exists for this profile
                    skill_exists = await sync_to_async(
                        lambda: ProfileSkill.objects.filter(profile=profile, skill=skill).exists()
                    )()
                    if not skill_exists:
                        # Create new profile skill relationship
                        profile_skill = await sync_to_async(ProfileSkill.objects.create)(
                            profile=profile,
                            skill=skill,
                            evidence_level='stated'
                        )

                        # Generate embedding for new profile skill
                        await sync_to_async(profile_skill.ensure_embedding)()

                        added_skills.append(skill_name)

            # Remove skills
            removed_skills = []
            if remove_skills:
                for skill_name in remove_skills:
                    # Find the skill
                    skill = await sync_to_async(
                        lambda sn=skill_name: Skill.objects.filter(name=sn).first()
                    )(skill_name)

                    if skill:
                        # Remove the ProfileSkill relationship
                        deleted_count, _ = await sync_to_async(
                            lambda: ProfileSkill.objects.filter(profile=profile, skill=skill).delete()
                        )()
                        if deleted_count > 0:
                            removed_skills.append(skill_name)

            # Add new experiences
            added_experiences = []
            if add_experiences:
                for exp_data in add_experiences:
                    # Get or create the organization
                    company_name = exp_data.get('company', 'Unknown Company')
                    organisation, created = await sync_to_async(Organisation.objects.get_or_create)(name=company_name)

                    # Parse dates
                    start_date = exp_data.get('start_date')
                    end_date = exp_data.get('end_date')

                    if isinstance(start_date, str):
                        try:
                            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                        except:
                            start_date = date(2020, 1, 1)  # Default fallback
                    elif not isinstance(start_date, date):
                        start_date = date(2020, 1, 1)

                    if end_date and isinstance(end_date, str):
                        try:
                            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                        except:
                            end_date = None
                    elif end_date and not isinstance(end_date, date):
                        end_date = None

                    # Create profile experience
                    await sync_to_async(ProfileExperience.objects.create)(
                        profile=profile,
                        organisation=organisation,
                        title=exp_data.get('title', 'Position'),
                        description=exp_data.get('description', ''),
                        start_date=start_date,
                        end_date=end_date
                    )
                    added_experiences.append(f"{exp_data.get('title', 'Position')} at {company_name}")

            # Build response
            result_parts = [f"✅ Profile updated successfully for {profile.first_name} {profile.last_name}"]

            if updated_fields:
                result_parts.append(f"\n📝 Updated: {', '.join(updated_fields)}")

            if added_skills:
                result_parts.append(f"\n➕ Added skills: {', '.join(added_skills)}")

            if removed_skills:
                result_parts.append(f"\n➖ Removed skills: {', '.join(removed_skills)}")

            if added_experiences:
                result_parts.append(f"\n💼 Added experiences: {', '.join(added_experiences)}")

            if not (updated_fields or added_skills or removed_skills or added_experiences):
                result_parts.append("\n📋 No changes were made to the profile.")

            return ''.join(result_parts)

        except Exception as e:
            return f"❌ Failed to update profile: {str(e)}"


class ListProfilesInput(BaseModel):
    """Input for listing profiles."""
    limit: Optional[int] = Field(default=20, description="Max profiles to list")
    search: Optional[str] = Field(default=None, description="Optional text search (name/email)")


class ListProfilesTool(BaseTool):
    """List profiles with filtering options."""

    name: str = "list_profiles"
    description: str = "List profiles (optionally filtered). Shows id, name, email for quick selection."
    args_schema: type[BaseModel] = ListProfilesInput

    def _run(self, limit: Optional[int] = 20, search: Optional[str] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the list profiles tool synchronously."""
        try:
            def fetch_profiles():
                qs = Profile.objects.all().order_by('-created_at')
                if search:
                    qs = qs.filter(first_name__icontains=search) | qs.filter(last_name__icontains=search) | qs.filter(email__icontains=search)
                return list(qs[: (limit or 20)])

            profiles = fetch_profiles()

            if not profiles:
                return "No profiles found."

            lines = [f"{p.first_name} {p.last_name} <{p.email}> id={p.id}" for p in profiles]
            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to list profiles: {str(e)}"

    async def _arun(self, limit: Optional[int] = 20, search: Optional[str] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the list profiles tool asynchronously."""
        try:
            def fetch_profiles():
                qs = Profile.objects.all().order_by('-created_at')
                if search:
                    qs = qs.filter(first_name__icontains=search) | qs.filter(last_name__icontains=search) | qs.filter(email__icontains=search)
                return list(qs[: (limit or 20)])

            profiles = await sync_to_async(fetch_profiles)()

            if not profiles:
                return "No profiles found."

            lines = [f"{p.first_name} {p.last_name} <{p.email}> id={p.id}" for p in profiles]
            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to list profiles: {str(e)}"


# =====================================================
# EXPORT ALL PROFILE TOOLS
# =====================================================

# Profile Management Tools (CRUD operations)
PROFILE_MANAGEMENT_TOOLS = [
    CreateProfileTool(),
    UpdateProfileTool(),
    UpdateUserProfileTool(),  # Profile-specific tool for current user with SSE updates
]

# Profile Discovery Tools (searching and listing)
PROFILE_DISCOVERY_TOOLS = [
    ListProfilesTool(),
]

# Combined profile tools for general use
PROFILE_TOOLS = PROFILE_MANAGEMENT_TOOLS + PROFILE_DISCOVERY_TOOLS

__all__ = [
    'PROFILE_TOOLS',
    'PROFILE_MANAGEMENT_TOOLS',
    'PROFILE_DISCOVERY_TOOLS',
    'CreateProfileTool',
    'UpdateProfileTool',
    'UpdateUserProfileTool',
    'ListProfilesTool',
]
