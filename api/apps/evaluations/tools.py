"""
Tools for evaluations app using LangChain BaseTool.
Provides tools for candidate-opportunity matching, evaluation, and analysis.
"""

from typing import Optional, List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from pydantic import BaseModel, Field

# Django imports
from asgiref.sync import sync_to_async

from apps.evaluations.services import EvaluationService


# =====================================================
# CANDIDATE DISCOVERY TOOLS
# =====================================================

class FindCandidatesInput(BaseModel):
    """Input for finding candidates for an opportunity."""
    opportunity_id: str = Field(description="UUID of the opportunity to find candidates for")
    llm_similarity_threshold: float = Field(
        default=0.7,
        description="Similarity threshold for LLM judging (0.0-1.0, default 0.7)"
    )
    limit: Optional[int] = Field(
        default=10,
        description="Maximum number of candidates to return (default 10)"
    )


class FindCandidatesForOpportunityTool(BaseTool):
    """Find the best candidates for a job opportunity."""

    name: str = "find_candidates_for_opportunity"
    description: str = """Find and rank the best candidates for a specific job opportunity.

    Uses TalentCo's multi-stage evaluation pipeline:
    1. Structured matching (skills overlap)
    2. Semantic similarity (vector embeddings)
    3. LLM judge evaluation for top matches

    Returns ranked candidates with detailed scores and reasoning."""

    args_schema: type[BaseModel] = FindCandidatesInput

    def _run(self, opportunity_id: str, llm_similarity_threshold: float = 0.7,
             limit: Optional[int] = 10, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the find candidates tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_evaluation():
                service = EvaluationService()
                result = await service.find_candidates_for_opportunity_async(
                    opportunity_id=opportunity_id,
                    llm_similarity_threshold=llm_similarity_threshold,
                    limit=limit
                )

                # Format for agent consumption
                summary = f"""Found {result['total_candidates_evaluated']} candidates for opportunity.
Top {len(result['top_matches'])} matches (LLM judged: {result['llm_judged_count']}):

"""

                for match in result['top_matches'][:5]:  # Show top 5 in summary
                    summary += f"#{match['rank']}: {match['candidate_name']} (Score: {match['final_score']:.3f})\n"
                    if match['was_llm_judged'] and match['llm_reasoning']:
                        summary += f"   💭 {match['llm_reasoning'][:100]}...\n"
                    summary += f"   📊 Structured: {match['structured_score']:.3f} | Semantic: {match['semantic_score']:.3f}\n\n"

                return summary + f"\nFull results available via evaluation_set_id: {result['evaluation_set_id']}"

            return run_evaluation()

        except Exception as e:
            return f"Error finding candidates: {str(e)}"

    async def _arun(self, opportunity_id: str, llm_similarity_threshold: float = 0.7,
                   limit: Optional[int] = 10, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the async find candidates tool."""
        try:
            service = EvaluationService()
            result = await service.find_candidates_for_opportunity_async(
                opportunity_id=opportunity_id,
                llm_similarity_threshold=llm_similarity_threshold,
                limit=limit
            )

            # Format for agent consumption
            summary = f"""Found {result['total_candidates_evaluated']} candidates for opportunity.
Top {len(result['top_matches'])} matches (LLM judged: {result['llm_judged_count']}):

"""

            for match in result['top_matches'][:5]:  # Show top 5 in summary
                summary += f"#{match['rank']}: {match['candidate_name']} (Score: {match['final_score']:.3f})\n"
                if match['was_llm_judged'] and match['llm_reasoning']:
                    summary += f"   💭 {match['llm_reasoning'][:100]}...\n"
                summary += f"   📊 Structured: {match['structured_score']:.3f} | Semantic: {match['semantic_score']:.3f}\n\n"

            return summary + f"\nFull results available via evaluation_set_id: {result['evaluation_set_id']}"

        except Exception as e:
            return f"Error finding candidates: {str(e)}"


class EvaluateCandidateInput(BaseModel):
    """Input for detailed candidate evaluation."""
    profile_id: str = Field(description="UUID of the candidate profile to evaluate")
    opportunity_id: str = Field(description="UUID of the opportunity to evaluate against")


class EvaluateCandidateProfileTool(BaseTool):
    """Perform detailed evaluation of a specific candidate for an opportunity."""

    name: str = "evaluate_candidate_profile"
    description: str = """Perform deep analysis of a specific candidate for an opportunity.

    Provides detailed breakdown of:
    - Structured matching scores
    - Semantic similarity analysis
    - LLM judge evaluation with reasoning
    - Skill fit analysis
    - Experience relevance assessment

    Use this for in-depth candidate assessment."""

    args_schema: type[BaseModel] = EvaluateCandidateInput

    def _run(self, profile_id: str, opportunity_id: str,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the candidate evaluation tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_evaluation():
                service = EvaluationService()
                result = await service.evaluate_single_candidate_async(
                    profile_id=profile_id,
                    opportunity_id=opportunity_id
                )

                scores = result['detailed_scores']

                evaluation = f"""🎯 Detailed Candidate Evaluation: {result['candidate_name']}

📊 Matching Scores:
• Combined Score: {scores['combined_score']:.3f} ({self._score_interpretation(scores['combined_score'])})
• Structured Match: {scores['structured_match']:.3f}
• Semantic Similarity: {scores['semantic_similarity']:.3f}
• LLM Judge Score: {scores['llm_judge_score']:.3f}

💭 LLM Assessment:
{scores['llm_reasoning']}

🔍 Skill Analysis:
{result['skill_analysis']['skill_overlap_percentage']:.1f}% skill overlap

📈 Experience Analysis:
{result['experience_analysis']['experience_relevance']:.1f}% experience relevance
"""
                return evaluation

            return run_evaluation()

        except Exception as e:
            return f"Error evaluating candidate: {str(e)}"

    async def _arun(self, profile_id: str, opportunity_id: str,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the async candidate evaluation tool."""
        try:
            service = EvaluationService()
            result = await service.evaluate_single_candidate_async(
                profile_id=profile_id,
                opportunity_id=opportunity_id
            )

            scores = result['detailed_scores']

            evaluation = f"""🎯 Detailed Candidate Evaluation: {result['candidate_name']}

📊 Matching Scores:
• Combined Score: {scores['combined_score']:.3f} ({self._score_interpretation(scores['combined_score'])})
• Structured Match: {scores['structured_match']:.3f}
• Semantic Similarity: {scores['semantic_similarity']:.3f}
• LLM Judge Score: {scores['llm_judge_score']:.3f}

💭 LLM Assessment:
{scores['llm_reasoning']}

🔍 Skill Analysis:
{result['skill_analysis']['skill_overlap_percentage']:.1f}% skill overlap

📈 Experience Analysis:
{result['experience_analysis']['experience_relevance']:.1f}% experience relevance
"""
            return evaluation

        except Exception as e:
            return f"Error evaluating candidate: {str(e)}"

    def _score_interpretation(self, score: float) -> str:
        """Interpret score for human readability."""
        if score >= 0.9: return "Excellent Match"
        elif score >= 0.8: return "Strong Match"
        elif score >= 0.7: return "Good Match"
        elif score >= 0.6: return "Moderate Match"
        else: return "Weak Match"


class AnalyzeTalentPoolInput(BaseModel):
    """Input for talent pool analysis."""
    skill_names: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific skills to analyze (if None, analyzes all skills)"
    )


class AnalyzeTalentPoolTool(BaseTool):
    """Analyze the available talent pool and skill market insights."""

    name: str = "analyze_talent_pool"
    description: str = """Analyze the current talent pool to understand:
    - Total candidate availability
    - Experience level distribution
    - Skill availability and scarcity
    - Market insights for hiring strategy

    Helpful for understanding talent market dynamics."""

    args_schema: type[BaseModel] = AnalyzeTalentPoolInput

    def _run(self, skill_names: Optional[List[str]] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the talent pool analysis tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_evaluation():
                service = EvaluationService()
                result = await service.analyze_talent_pool_async(skill_names=skill_names)

                exp_dist = result['experience_distribution']
                insights = result['market_insights']

                analysis = f"""📊 Talent Pool Analysis ({result['total_candidates']} candidates)

👥 Experience Distribution:
• Junior (0-3 years): {exp_dist['junior']} candidates ({exp_dist['junior']/result['total_candidates']*100:.1f}%)
• Mid-level (3-7 years): {exp_dist['mid']} candidates ({exp_dist['mid']/result['total_candidates']*100:.1f}%)
• Senior (7-15 years): {exp_dist['senior']} candidates ({exp_dist['senior']/result['total_candidates']*100:.1f}%)
• Executive (15+ years): {exp_dist['executive']} candidates ({exp_dist['executive']/result['total_candidates']*100:.1f}%)

🔥 Most In-Demand Skills:
"""
                for skill, data in insights['most_common_skills'][:5]:
                    analysis += f"• {skill}: {data['count']} candidates\n"

                analysis += f"\n💎 Scarce Skills (high value):\n"
                for skill in insights['skill_scarcity'][:5]:
                    analysis += f"• {skill}\n"

                return analysis

            return run_evaluation()

        except Exception as e:
            return f"Error analyzing talent pool: {str(e)}"

    async def _arun(self, skill_names: Optional[List[str]] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the async talent pool analysis tool."""
        try:
            service = EvaluationService()
            result = await service.analyze_talent_pool_async(skill_names=skill_names)

            exp_dist = result['experience_distribution']
            insights = result['market_insights']

            analysis = f"""📊 Talent Pool Analysis ({result['total_candidates']} candidates)

👥 Experience Distribution:
• Junior (0-3 years): {exp_dist['junior']} candidates ({exp_dist['junior']/result['total_candidates']*100:.1f}%)
• Mid-level (3-7 years): {exp_dist['mid']} candidates ({exp_dist['mid']/result['total_candidates']*100:.1f}%)
• Senior (7-15 years): {exp_dist['senior']} candidates ({exp_dist['senior']/result['total_candidates']*100:.1f}%)
• Executive (15+ years): {exp_dist['executive']} candidates ({exp_dist['executive']/result['total_candidates']*100:.1f}%)

🔥 Most In-Demand Skills:
"""
            for skill, data in insights['most_common_skills'][:5]:
                analysis += f"• {skill}: {data['count']} candidates\n"

            analysis += f"\n💎 Scarce Skills (high value):\n"
            for skill in insights['skill_scarcity'][:5]:
                analysis += f"• {skill}\n"

            return analysis

        except Exception as e:
            return f"Error analyzing talent pool: {str(e)}"


# =====================================================
# OPPORTUNITY DISCOVERY TOOLS
# =====================================================

class FindOpportunitiesInput(BaseModel):
    """Input for finding opportunities for a profile."""
    profile_id: str = Field(description="UUID of the profile to find opportunities for")
    llm_similarity_threshold: float = Field(
        default=0.7,
        description="Similarity threshold for LLM judging (0.0-1.0, default 0.7)"
    )
    limit: Optional[int] = Field(
        default=10,
        description="Maximum number of opportunities to return (default 10)"
    )


class FindOpportunitiesForProfileTool(BaseTool):
    """Find the best job opportunities for a candidate profile."""

    name: str = "find_opportunities_for_profile"
    description: str = """Find and rank the best job opportunities for a specific candidate.

    Uses TalentCo's multi-stage evaluation pipeline:
    1. Structured matching (skills overlap)
    2. Semantic similarity (vector embeddings)
    3. LLM judge evaluation for top matches

    Returns ranked opportunities with detailed scores and reasoning."""

    args_schema: type[BaseModel] = FindOpportunitiesInput

    def _run(self, profile_id: str, llm_similarity_threshold: float = 0.7,
             limit: Optional[int] = 10, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the find opportunities tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_evaluation():
                service = EvaluationService()
                result = await service.find_opportunities_for_profile_async(
                    profile_id=profile_id,
                    llm_similarity_threshold=llm_similarity_threshold,
                    limit=limit
                )

                # Format for agent consumption
                summary = f"""Found {result['total_opportunities_evaluated']} opportunities for your profile.
Top {len(result['top_matches'])} matches (LLM analyzed: {result['llm_judged_count']}):

"""

                for match in result['top_matches'][:5]:  # Show top 5 in summary
                    summary += f"#{match['rank']}: {match['role_title']} at {match['company_name']} (Score: {match['final_score']:.3f})\n"
                    if match['was_llm_judged'] and match['llm_reasoning']:
                        summary += f"   💭 {match['llm_reasoning'][:100]}...\n"
                    summary += f"   📊 Structured: {match['structured_score']:.3f} | Semantic: {match['semantic_score']:.3f}\n\n"

                return summary + f"\nFull results available via evaluation_set_id: {result['evaluation_set_id']}"

            return run_evaluation()

        except Exception as e:
            return f"Error finding opportunities: {str(e)}"

    async def _arun(self, profile_id: str, llm_similarity_threshold: float = 0.7,
                   limit: Optional[int] = 10, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the async find opportunities tool."""
        try:
            service = EvaluationService()
            result = await service.find_opportunities_for_profile_async(
                profile_id=profile_id,
                llm_similarity_threshold=llm_similarity_threshold,
                limit=limit
            )

            # Format for agent consumption
            summary = f"""Found {result['total_opportunities_evaluated']} opportunities for your profile.
Top {len(result['top_matches'])} matches (LLM analyzed: {result['llm_judged_count']}):

"""

            for match in result['top_matches'][:5]:  # Show top 5 in summary
                summary += f"#{match['rank']}: {match['role_title']} at {match['company_name']} (Score: {match['final_score']:.3f})\n"
                if match['was_llm_judged'] and match['llm_reasoning']:
                    summary += f"   💭 {match['llm_reasoning'][:100]}...\n"
                summary += f"   📊 Structured: {match['structured_score']:.3f} | Semantic: {match['semantic_score']:.3f}\n\n"

            return summary + f"\nFull results available via evaluation_set_id: {result['evaluation_set_id']}"

        except Exception as e:
            return f"Error finding opportunities: {str(e)}"


class AnalyzeOpportunityFitInput(BaseModel):
    """Input for analyzing opportunity fit."""
    profile_id: str = Field(description="UUID of the candidate profile")
    opportunity_id: str = Field(description="UUID of the opportunity to analyze")


class AnalyzeOpportunityFitTool(BaseTool):
    """Analyze how well a specific opportunity fits a candidate's profile."""

    name: str = "analyze_opportunity_fit"
    description: str = """Perform detailed analysis of opportunity fit for a candidate.

    Provides detailed breakdown of:
    - Overall fit assessment
    - Skill gap analysis
    - Experience relevance
    - LLM assessment with reasoning

    Use this to help candidates understand opportunity compatibility."""

    args_schema: type[BaseModel] = AnalyzeOpportunityFitInput

    def _run(self, profile_id: str, opportunity_id: str,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the opportunity fit analysis tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_evaluation():
                service = EvaluationService()
                result = await service.analyze_opportunity_fit_async(
                    profile_id=profile_id,
                    opportunity_id=opportunity_id
                )

                fit = result['fit_analysis']

                analysis = f"""🎯 Opportunity Fit Analysis: {result['role_title']} at {result['company_name']}

📊 Fit Assessment:
• Overall Fit: {fit['combined_score']:.3f} ({self._score_interpretation(fit['combined_score'])})
• Structured Match: {fit['structured_match']:.3f}
• Semantic Similarity: {fit['semantic_similarity']:.3f}
• LLM Assessment: {fit['llm_assessment_score']:.3f}

💭 AI Analysis:
{fit['llm_reasoning']}

🔍 Skill Gap Analysis:
{result['skill_gap_analysis']['skill_overlap_percentage']:.1f}% of your skills match this role

📈 Experience Relevance:
{result['experience_relevance']['experience_relevance']:.1f}% of your experience is relevant
"""
                return analysis

            return run_evaluation()

        except Exception as e:
            return f"Error analyzing opportunity fit: {str(e)}"

    async def _arun(self, profile_id: str, opportunity_id: str,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the async opportunity fit analysis tool."""
        try:
            service = EvaluationService()
            result = await service.analyze_opportunity_fit_async(
                profile_id=profile_id,
                opportunity_id=opportunity_id
            )

            fit = result['fit_analysis']

            analysis = f"""🎯 Opportunity Fit Analysis: {result['role_title']} at {result['company_name']}

📊 Fit Assessment:
• Overall Fit: {fit['combined_score']:.3f} ({self._score_interpretation(fit['combined_score'])})
• Structured Match: {fit['structured_match']:.3f}
• Semantic Similarity: {fit['semantic_similarity']:.3f}
• LLM Assessment: {fit['llm_assessment_score']:.3f}

💭 AI Analysis:
{fit['llm_reasoning']}

🔍 Skill Gap Analysis:
{result['skill_gap_analysis']['skill_overlap_percentage']:.1f}% of your skills match this role

📈 Experience Relevance:
{result['experience_relevance']['experience_relevance']:.1f}% of your experience is relevant
"""
            return analysis

        except Exception as e:
            return f"Error analyzing opportunity fit: {str(e)}"

    def _score_interpretation(self, score: float) -> str:
        """Interpret score for human readability."""
        if score >= 0.9: return "Excellent Fit"
        elif score >= 0.8: return "Strong Fit"
        elif score >= 0.7: return "Good Fit"
        elif score >= 0.6: return "Moderate Fit"
        else: return "Weak Fit"


class GetLearningRecommendationsInput(BaseModel):
    """Input for learning recommendations."""
    profile_id: str = Field(description="UUID of the candidate profile")
    target_opportunities: Optional[List[str]] = Field(
        default=None,
        description="Optional list of opportunity IDs to analyze (if None, analyzes all opportunities)"
    )


class GetLearningRecommendationsTool(BaseTool):
    """Get personalized learning and skill development recommendations."""

    name: str = "get_learning_recommendations"
    description: str = """Analyze skill gaps and provide personalized learning recommendations.

    Provides:
    - Current skill inventory
    - Priority skill recommendations based on market demand
    - Learning path suggestions (immediate, medium-term, advanced)
    - Impact assessment for each recommended skill

    Helps candidates plan their skill development strategy."""

    args_schema: type[BaseModel] = GetLearningRecommendationsInput

    def _run(self, profile_id: str, target_opportunities: Optional[List[str]] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute the learning recommendations tool synchronously."""
        try:
            from asgiref.sync import async_to_sync

            @async_to_sync
            async def run_evaluation():
                service = EvaluationService()
                result = await service.get_learning_recommendations_async(
                    profile_id=profile_id,
                    target_opportunities=target_opportunities
                )

                gap_analysis = result['skill_gap_analysis']
                learning_path = result['learning_path']

                recommendations = f"""📚 Personalized Learning Recommendations

📊 Current State:
• Your skills: {result['current_skills_count']}
• Skills gaps identified: {gap_analysis['missing_skills_count']}

🎯 Priority Recommendations:
"""
                for rec in gap_analysis['priority_recommendations'][:5]:
                    impact_emoji = "🔥" if rec['impact'] == 'high' else "📈"
                    recommendations += f"{impact_emoji} {rec['skill_name']} ({rec['impact']} impact)\n"
                    recommendations += f"   • Appears in {rec['opportunity_count']} opportunities\n"
                    if rec['example_opportunities']:
                        recommendations += f"   • Example roles: {', '.join([opp['title'] for opp in rec['example_opportunities'][:2]])}\n"
                    recommendations += "\n"

                recommendations += f"""🛤️ Suggested Learning Path:

🚀 Immediate Focus (next 3 months):
{', '.join(learning_path['immediate_focus'])}

📈 Medium Term (3-6 months):
{', '.join(learning_path['medium_term'])}

🎓 Advanced (6+ months):
{', '.join(learning_path['advanced'])}
"""
                return recommendations

            return run_evaluation()

        except Exception as e:
            return f"Error generating learning recommendations: {str(e)}"

    async def _arun(self, profile_id: str, target_opportunities: Optional[List[str]] = None,
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """Execute the async learning recommendations tool."""
        try:
            service = EvaluationService()
            result = await service.get_learning_recommendations_async(
                profile_id=profile_id,
                target_opportunities=target_opportunities
            )

            gap_analysis = result['skill_gap_analysis']
            learning_path = result['learning_path']

            recommendations = f"""📚 Personalized Learning Recommendations

📊 Current State:
• Your skills: {result['current_skills_count']}
• Skills gaps identified: {gap_analysis['missing_skills_count']}

🎯 Priority Recommendations:
"""
            for rec in gap_analysis['priority_recommendations'][:5]:
                impact_emoji = "🔥" if rec['impact'] == 'high' else "📈"
                recommendations += f"{impact_emoji} {rec['skill_name']} ({rec['impact']} impact)\n"
                recommendations += f"   • Appears in {rec['opportunity_count']} opportunities\n"
                if rec['example_opportunities']:
                    recommendations += f"   • Example roles: {', '.join([opp['title'] for opp in rec['example_opportunities'][:2]])}\n"
                recommendations += "\n"

            recommendations += f"""🛤️ Suggested Learning Path:

🚀 Immediate Focus (next 3 months):
{', '.join(learning_path['immediate_focus'])}

📈 Medium Term (3-6 months):
{', '.join(learning_path['medium_term'])}

🎓 Advanced (6+ months):
{', '.join(learning_path['advanced'])}
"""
            return recommendations

        except Exception as e:
            return f"Error generating learning recommendations: {str(e)}"


# =====================================================
# EXPORT ALL EVALUATION TOOLS
# =====================================================

# Employer Evaluation Tools (for recruiters and hiring managers)
EMPLOYER_EVALUATION_TOOLS = [
    FindCandidatesForOpportunityTool(),
    EvaluateCandidateProfileTool(),
    AnalyzeTalentPoolTool(),
]

# Candidate Evaluation Tools (for job seekers and career development)
CANDIDATE_EVALUATION_TOOLS = [
    FindOpportunitiesForProfileTool(),
    AnalyzeOpportunityFitTool(),
    GetLearningRecommendationsTool(),
]

# Combined evaluation tools for general use
EVALUATION_TOOLS = EMPLOYER_EVALUATION_TOOLS + CANDIDATE_EVALUATION_TOOLS

__all__ = [
    'EVALUATION_TOOLS',
    'EMPLOYER_EVALUATION_TOOLS',
    'CANDIDATE_EVALUATION_TOOLS',
    'FindCandidatesForOpportunityTool',
    'EvaluateCandidateProfileTool',
    'AnalyzeTalentPoolTool',
    'FindOpportunitiesForProfileTool',
    'AnalyzeOpportunityFitTool',
    'GetLearningRecommendationsTool',
]
