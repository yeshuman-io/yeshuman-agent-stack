"""
Tests for applications API endpoints.
Simple service-direct pattern for maintainable tests.
"""

import pytest
from apps.applications.services import ApplicationService
from apps.applications.factories import (
    OrganisationFactory,
    ProfileFactory,
    OpportunityFactory,
    ApplicationFactory,
    StageTemplateFactory
)


class TestApplicationsAPI:
    """Test applications API business logic."""

    @pytest.mark.asyncio
    async def test_create_application_endpoint(self):
        """Test creating an application through service."""
        from asgiref.sync import sync_to_async

        # Create test data (sync operations in async context)
        organisation = await sync_to_async(OrganisationFactory)()
        profile = await sync_to_async(ProfileFactory)()
        opportunity = await sync_to_async(OpportunityFactory)(organisation=organisation)

        # Seed stages
        service = ApplicationService()
        await sync_to_async(service.seed_default_stages)()

        # Test the creation
        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id),
            source="direct"
        )

        assert result.created is True
        assert result.application.status == "applied"
        assert result.application.source == "direct"

    def test_list_applications_endpoint(self):
        """Test listing applications."""
        # Create test data
        organisation = OrganisationFactory()
        profile = ProfileFactory()
        opportunity = OpportunityFactory(organisation=organisation)
        application = ApplicationFactory(
            profile=profile,
            opportunity=opportunity
        )

        # Test listing
        applications = list(application.__class__.objects.all())
        assert len(applications) >= 1
        assert application in applications


class TestStageManagementAPI:
    """Test stage management business logic."""

    def test_seed_stages_endpoint(self):
        """Test seeding default stages."""
        service = ApplicationService()
        stages = service.seed_default_stages()

        assert len(stages) == 7
        stage_names = [s.name for s in stages]
        assert "Applied" in stage_names
        assert "Hired" in stage_names

    def test_list_stages_endpoint(self):
        """Test listing stages."""
        # Seed stages first
        service = ApplicationService()
        service.seed_default_stages()

        # Test listing
        stages = list(StageTemplateFactory._meta.model.objects.all())
        assert len(stages) >= 7


class TestApplicationActionsAPI:
    """Test application actions business logic."""

    @pytest.mark.asyncio
    async def test_change_stage_endpoint(self):
        """Test changing application stage."""
        from asgiref.sync import sync_to_async

        # Create test data (sync operations in async context)
        organisation = await sync_to_async(OrganisationFactory)()
        profile = await sync_to_async(ProfileFactory)()
        opportunity = await sync_to_async(OpportunityFactory)(organisation=organisation)

        service = ApplicationService()
        await sync_to_async(service.seed_default_stages)()

        # Create application
        result = await service.create_application(
            profile_id=str(profile.id),
            opportunity_id=str(opportunity.id),
            source="direct"
        )

        # Change stage to "in_review"
        updated_app = await service.change_stage(
            application_id=str(result.application.id),
            stage_slug="in_review"
        )

        assert updated_app.status == "in_review"
