"""
Tests for opportunities app tools.
"""

from django.test import TestCase
from apps.opportunities.tools import CreateOpportunityTool, UpdateOpportunityTool, ListOpportunitiesTool


class TestOpportunitiesTools(TestCase):
    """Light tests for opportunities tools functionality."""

    def test_create_opportunity_tool(self):
        """Test create opportunity tool basic functionality."""
        # Test the tool (using sync version for Django test compatibility)
        tool = CreateOpportunityTool()
        result = tool._run(
            title="Test Software Engineer",
            company_name="Test Company",
            location="Remote",
            description="A great job",
            required_skills=["Python", "Django"]
        )

        # Basic assertions
        self.assertIn("✅ Job opportunity created successfully", result)
        self.assertIn("Test Software Engineer", result)
        self.assertIn("Test Company", result)

    def test_update_opportunity_tool(self):
        """Test update opportunity tool basic functionality."""
        from apps.organisations.factories import OrganisationFactory
        from apps.opportunities.factories import OpportunityFactory

        # Create test data
        organisation = OrganisationFactory()
        opportunity = OpportunityFactory(organisation=organisation)

        # Test the tool (sync version for simplicity)
        tool = UpdateOpportunityTool()
        result = tool._run(
            opportunity_id=str(opportunity.id),
            title="Updated Title",
            description="Updated description"
        )

        # Basic assertions
        self.assertIn("✅ Opportunity updated successfully", result)
        self.assertIn("Updated Title", result)

    def test_list_opportunities_tool(self):
        """Test list opportunities tool basic functionality."""
        from apps.organisations.factories import OrganisationFactory
        from apps.opportunities.factories import OpportunityFactory

        # Create test data
        organisation = OrganisationFactory()
        opportunity = OpportunityFactory(organisation=organisation)

        # Test the tool
        tool = ListOpportunitiesTool()
        result = tool._run(limit=10)

        # Basic assertions
        self.assertGreater(len(result), 0)  # Should return some results
