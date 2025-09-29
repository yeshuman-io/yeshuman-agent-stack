"""
Tests for evaluations app tools.
"""

from django.test import TestCase
from apps.evaluations.tools import (
    FindCandidatesForOpportunityTool,
    EvaluateCandidateProfileTool,
    AnalyzeTalentPoolTool,
    FindOpportunitiesForProfileTool,
    AnalyzeOpportunityFitTool,
    GetLearningRecommendationsTool
)


class TestEvaluationsTools(TestCase):
    """Light tests for evaluations tools functionality."""

    def test_find_candidates_tool_instantiation(self):
        """Test find candidates tool can be instantiated."""
        tool = FindCandidatesForOpportunityTool()
        self.assertEqual(tool.name, "find_candidates_for_opportunity")
        self.assertIsNotNone(tool.args_schema)

    def test_evaluate_candidate_tool_instantiation(self):
        """Test evaluate candidate tool can be instantiated."""
        tool = EvaluateCandidateProfileTool()
        self.assertEqual(tool.name, "evaluate_candidate_profile")
        self.assertIsNotNone(tool.args_schema)

    def test_analyze_talent_pool_tool_instantiation(self):
        """Test analyze talent pool tool can be instantiated."""
        tool = AnalyzeTalentPoolTool()
        self.assertEqual(tool.name, "analyze_talent_pool")
        self.assertIsNotNone(tool.args_schema)

    def test_find_opportunities_tool_instantiation(self):
        """Test find opportunities tool can be instantiated."""
        tool = FindOpportunitiesForProfileTool()
        self.assertEqual(tool.name, "find_opportunities_for_profile")
        self.assertIsNotNone(tool.args_schema)

    def test_analyze_opportunity_fit_tool_instantiation(self):
        """Test analyze opportunity fit tool can be instantiated."""
        tool = AnalyzeOpportunityFitTool()
        self.assertEqual(tool.name, "analyze_opportunity_fit")
        self.assertIsNotNone(tool.args_schema)

    def test_get_learning_recommendations_tool_instantiation(self):
        """Test get learning recommendations tool can be instantiated."""
        tool = GetLearningRecommendationsTool()
        self.assertEqual(tool.name, "get_learning_recommendations")
        self.assertIsNotNone(tool.args_schema)






