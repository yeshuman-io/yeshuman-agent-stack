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
    'ListProfilesTool',
]
