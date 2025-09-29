"""
Tools for opportunities app using LangChain BaseTool.
Provides tools for managing job opportunities, candidate discovery, and talent pool analysis.
"""

from typing import Optional, List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from pydantic import BaseModel, Field
from datetime import datetime

# Django imports
from asgiref.sync import sync_to_async

from apps.opportunities.models import Opportunity, OpportunitySkill
from apps.organisations.models import Organisation
from apps.skills.models import Skill


# =====================================================
# OPPORTUNITY MANAGEMENT TOOLS
# =====================================================

class CreateOpportunityInput(BaseModel):
    """Input for creating a new job opportunity."""
    title: str = Field(description="Job title/role name")
    company_name: str = Field(description="Company/organization name")
    location: Optional[str] = Field(
        default="Not specified",
        description="Job location (e.g., 'Remote', 'New York, NY')"
    )
    description: Optional[str] = Field(
        default="Job description not provided",
        description="Detailed job description"
    )
    required_skills: Optional[List[str]] = Field(
        default=None,
        description="List of required skills for the role"
    )
    salary_range: Optional[str] = Field(
        default=None,
        description="Salary range (e.g., '$80,000 - $120,000')"
    )


class CreateOpportunityTool(BaseTool):
    """Create a new job opportunity in the system."""

    name: str = "create_opportunity"
    description: str = """Create a new job opportunity that can be used for candidate matching.

    This tool:
    - Creates the opportunity in the database
    - Sets up required skills if provided
    - Returns the opportunity ID for use with other tools
    - Enables candidate matching via find_candidates_for_opportunity

    Use this when you need to post a new job or when an opportunity mentioned
    in conversation doesn't exist in the system yet."""

    args_schema: type[BaseModel] = CreateOpportunityInput

    def _run(self, title: str, company_name: str, location: Optional[str] = "Not specified",
             description: Optional[str] = "Job description not provided",
             required_skills: Optional[List[str]] = None, salary_range: Optional[str] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the create opportunity tool synchronously."""
        try:
            import asyncio
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                # Get or create the organization
                organisation, created = await sync_to_async(Organisation.objects.get_or_create)(
                    name=company_name
                )

                # Create the opportunity
                opportunity = await sync_to_async(Opportunity.objects.create)(
                    title=title,
                    organisation=organisation,
                    description=description
                )

                # Add required skills if provided
                created_skills = []
                if required_skills:
                    for skill_name in required_skills:
                        # Get or create the skill (Skill model only has name field)
                        skill, skill_created = await sync_to_async(Skill.objects.get_or_create)(
                            name=skill_name
                        )

                        # Create opportunity skill relationship
                        opp_skill = await sync_to_async(OpportunitySkill.objects.create)(
                            opportunity=opportunity,
                            skill=skill,
                            requirement_type='required'
                        )

                        # Generate embedding for new opportunity skill
                        await sync_to_async(opp_skill.ensure_embedding)()

                        created_skills.append(skill_name)

                return opportunity, created_skills

            opportunity, created_skills = run_service()

            skills_summary = f"\n• Required skills: {', '.join(created_skills)}" if created_skills else ""

            result = f"""✅ Job opportunity created successfully!

📋 Opportunity Details:
• Title: {title}
• Company: {company_name}
• Opportunity ID: {opportunity.id}{skills_summary}

🎯 Next Steps:
You can now use find_candidates_for_opportunity with ID: {opportunity.id}
"""

            return result

        except Exception as e:
            return f"❌ Failed to create opportunity: {str(e)}"

    async def _arun(self, title: str, company_name: str, location: Optional[str] = "Not specified",
                   description: Optional[str] = "Job description not provided",
                   required_skills: Optional[List[str]] = None, salary_range: Optional[str] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the create opportunity tool asynchronously."""
        try:
            # Get or create the organization
            organisation, created = await sync_to_async(Organisation.objects.get_or_create)(
                name=company_name
            )

            # Create the opportunity
            opportunity = await sync_to_async(Opportunity.objects.create)(
                title=title,
                organisation=organisation,
                description=description
            )

            # Add required skills if provided
            created_skills = []
            if required_skills:
                for skill_name in required_skills:
                    # Get or create the skill
                    skill, skill_created = await sync_to_async(Skill.objects.get_or_create)(
                        name=skill_name
                    )

                    # Create opportunity skill relationship
                    opp_skill = await sync_to_async(OpportunitySkill.objects.create)(
                        opportunity=opportunity,
                        skill=skill,
                        requirement_type='required'
                    )

                    # Generate embedding for new opportunity skill
                    await sync_to_async(opp_skill.ensure_embedding)()

                    created_skills.append(skill_name)

            skills_summary = f"\n• Required skills: {', '.join(created_skills)}" if created_skills else ""

            result = f"""✅ Job opportunity created successfully!

📋 Opportunity Details:
• Title: {title}
• Company: {company_name}
• Opportunity ID: {opportunity.id}{skills_summary}

🎯 Next Steps:
You can now use find_candidates_for_opportunity with ID: {opportunity.id}
"""

            return result

        except Exception as e:
            return f"❌ Failed to create opportunity: {str(e)}"


class UpdateOpportunityInput(BaseModel):
    """Input for updating an existing job opportunity."""
    opportunity_id: str = Field(description="UUID of the opportunity to update")
    title: Optional[str] = Field(default=None, description="New job title (optional)")
    description: Optional[str] = Field(default=None, description="New job description (optional)")
    organization_name: Optional[str] = Field(default=None, description="New organization name (optional)")
    add_skills: Optional[List[str]] = Field(
        default=None,
        description="List of required skills to add to the opportunity"
    )
    remove_skills: Optional[List[str]] = Field(
        default=None,
        description="List of skills to remove from the opportunity"
    )


class UpdateOpportunityTool(BaseTool):
    """Update an existing job opportunity."""

    name: str = "update_opportunity"
    description: str = """Update an existing job opportunity with new information.

    This tool can:
    - Update job title and description
    - Change organization information
    - Add new required skills
    - Remove existing skills
    - Generate embeddings for any new data

    Use this when you need to modify existing job postings or update requirements."""

    args_schema: type[BaseModel] = UpdateOpportunityInput

    def _run(self, opportunity_id: str, title: Optional[str] = None, description: Optional[str] = None,
             organization_name: Optional[str] = None, add_skills: Optional[List[str]] = None,
             remove_skills: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the update opportunity tool synchronously."""
        try:
            import asyncio
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_service():
                return await self._update_opportunity_async(
                    opportunity_id, title, description, organization_name, add_skills, remove_skills
                )

            return run_service()

        except Exception as e:
            return f"❌ Failed to update opportunity: {str(e)}"

    async def _arun(self, opportunity_id: str, title: Optional[str] = None, description: Optional[str] = None,
                   organization_name: Optional[str] = None, add_skills: Optional[List[str]] = None,
                   remove_skills: Optional[List[str]] = None, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the update opportunity tool asynchronously."""
        return await self._update_opportunity_async(
            opportunity_id, title, description, organization_name, add_skills, remove_skills
        )

    async def _update_opportunity_async(self, opportunity_id: str, title: Optional[str] = None,
                                       description: Optional[str] = None, organization_name: Optional[str] = None,
                                       add_skills: Optional[List[str]] = None, remove_skills: Optional[List[str]] = None) -> str:
        """Internal method to update opportunity."""
        try:
            # Get the existing opportunity
            opportunity = await sync_to_async(
                Opportunity.objects.select_related('organisation').get
            )(id=opportunity_id)

            updated_fields = []

            # Update basic opportunity information
            opportunity_updated = False
            if title:
                opportunity.title = title
                opportunity_updated = True
                updated_fields.append(f"Title: {title}")

            if description:
                opportunity.description = description
                opportunity_updated = True
                updated_fields.append(f"Description updated")

            # Update organization if specified
            if organization_name:
                organisation, created = await sync_to_async(Organisation.objects.get_or_create)(
                    name=organization_name
                )
                opportunity.organisation = organisation
                opportunity_updated = True
                updated_fields.append(f"Organization: {organization_name}")

            if opportunity_updated:
                await sync_to_async(opportunity.save)()

            # Add new skills
            added_skills = []
            if add_skills:
                for skill_name in add_skills:
                    # Get or create the skill
                    skill, skill_created = await sync_to_async(Skill.objects.get_or_create)(
                        name=skill_name
                    )

                    # Check if skill already exists for this opportunity
                    skill_exists = await sync_to_async(
                        lambda: OpportunitySkill.objects.filter(opportunity=opportunity, skill=skill).exists()
                    )()
                    if not skill_exists:
                        # Create new opportunity skill relationship
                        opp_skill = await sync_to_async(OpportunitySkill.objects.create)(
                            opportunity=opportunity,
                            skill=skill,
                            requirement_type='required'
                        )

                        # Generate embedding for new opportunity skill
                        await sync_to_async(opp_skill.ensure_embedding)()

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
                        # Remove the OpportunitySkill relationship
                        deleted_count, _ = await sync_to_async(
                            lambda: OpportunitySkill.objects.filter(opportunity=opportunity, skill=skill).delete()
                        )()
                        if deleted_count > 0:
                            removed_skills.append(skill_name)

            # Build response
            result_parts = [f"✅ Opportunity updated successfully: {opportunity.title} at {opportunity.organisation.name}"]

            if updated_fields:
                result_parts.append(f"\n📝 Updated: {', '.join(updated_fields)}")

            if added_skills:
                result_parts.append(f"\n➕ Added skills: {', '.join(added_skills)}")

            if removed_skills:
                result_parts.append(f"\n➖ Removed skills: {', '.join(removed_skills)}")

            if not (updated_fields or added_skills or removed_skills):
                result_parts.append("\n📋 No changes were made to the opportunity.")

            return ''.join(result_parts)

        except Exception as e:
            return f"❌ Failed to update opportunity: {str(e)}"


class ListOpportunitiesInput(BaseModel):
    """Input for listing opportunities."""
    limit: Optional[int] = Field(default=20, description="Max opportunities to list")
    search: Optional[str] = Field(default=None, description="Optional text search (title/org)")


class ListOpportunitiesTool(BaseTool):
    """List opportunities with filtering options."""

    name: str = "list_opportunities"
    description: str = "List opportunities (optionally filtered). Shows id, title, organisation, and counts."
    args_schema: type[BaseModel] = ListOpportunitiesInput

    def _run(self, limit: Optional[int] = 20, search: Optional[str] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the list opportunities tool synchronously."""
        try:
            from django.db.models import Count

            def fetch_opportunities():
                qs = Opportunity.objects.select_related('organisation').annotate(
                    questions_count=Count('questions'), skills_count=Count('opportunity_skills')
                ).order_by('-created_at')

                if search:
                    qs = qs.filter(title__icontains=search) | qs.filter(organisation__name__icontains=search)

                return list(qs[: (limit or 20)])

            opportunities = fetch_opportunities()

            if not opportunities:
                return "No opportunities found."

            lines = [f"{o.title} @ {o.organisation.name} id={o.id} (Q:{getattr(o,'questions_count',0)} S:{getattr(o,'skills_count',0)})" for o in opportunities]
            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to list opportunities: {str(e)}"

    async def _arun(self, limit: Optional[int] = 20, search: Optional[str] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the list opportunities tool asynchronously."""
        try:
            from django.db.models import Count

            def fetch_opportunities():
                qs = Opportunity.objects.select_related('organisation').annotate(
                    questions_count=Count('questions'), skills_count=Count('opportunity_skills')
                ).order_by('-created_at')

                if search:
                    qs = qs.filter(title__icontains=search) | qs.filter(organisation__name__icontains=search)

                return list(qs[: (limit or 20)])

            opportunities = await sync_to_async(fetch_opportunities)()

            if not opportunities:
                return "No opportunities found."

            lines = [f"{o.title} @ {o.organisation.name} id={o.id} (Q:{getattr(o,'questions_count',0)} S:{getattr(o,'skills_count',0)})" for o in opportunities]
            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to list opportunities: {str(e)}"


# =====================================================
# EXPORT ALL OPPORTUNITY TOOLS
# =====================================================

# Opportunity Management Tools (CRUD operations)
OPPORTUNITY_MANAGEMENT_TOOLS = [
    CreateOpportunityTool(),
    UpdateOpportunityTool(),
]

# Opportunity Discovery Tools (searching and listing)
OPPORTUNITY_DISCOVERY_TOOLS = [
    ListOpportunitiesTool(),
]

# Combined opportunity tools for general use
OPPORTUNITY_TOOLS = OPPORTUNITY_MANAGEMENT_TOOLS + OPPORTUNITY_DISCOVERY_TOOLS

__all__ = [
    'OPPORTUNITY_TOOLS',
    'OPPORTUNITY_MANAGEMENT_TOOLS',
    'OPPORTUNITY_DISCOVERY_TOOLS',
    'CreateOpportunityTool',
    'UpdateOpportunityTool',
    'ListOpportunitiesTool',
]
