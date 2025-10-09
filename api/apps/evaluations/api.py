"""
API endpoints for evaluations app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List, Optional
from apps.evaluations.models import EvaluationSet, Evaluation

# Create router for evaluations endpoints
evaluations_router = Router()


class EvaluationSchema(Schema):
    """Schema for Evaluation model."""
    id: str
    profile_id: str
    opportunity_id: str
    opportunity_title: str
    opportunity_organisation_name: str
    candidate_name: Optional[str] = None  # For employer perspective
    final_score: float
    rank_in_set: int
    was_llm_judged: bool
    llm_reasoning: Optional[str]
    structured_score: float
    semantic_score: float


class EvaluationSetSchema(Schema):
    """Schema for EvaluationSet model."""
    id: str
    evaluator_perspective: str
    opportunity_id: Optional[str] = None
    profile_id: Optional[str] = None
    total_evaluated: int
    llm_judged_count: int
    is_complete: bool
    evaluations: List[EvaluationSchema]


class MatchResultSchema(Schema):
    """Schema for individual match results."""
    rank: int
    opportunity_id: str
    role_title: str
    company_name: str
    final_score: float
    structured_score: float
    semantic_score: float
    llm_score: Optional[float]
    llm_reasoning: Optional[str]
    was_llm_judged: bool


class MatchingResponseSchema(Schema):
    """Response schema for profile-opportunity matching."""
    evaluation_set_id: str
    profile_id: str
    total_opportunities_evaluated: int
    llm_judged_count: int
    top_matches: List[MatchResultSchema]


class OpportunityFitAnalysisSchema(Schema):
    """Detailed analysis of opportunity fit for a candidate."""
    profile_id: str
    opportunity_id: str
    role_title: str
    company_name: str
    fit_analysis: dict  # Contains structured_match, semantic_similarity, combined_score, llm_assessment_score, llm_reasoning
    skill_gap_analysis: Optional[dict]
    experience_relevance: Optional[dict]


class MatchingRequestSchema(Schema):
    """Request schema for matching operations."""
    llm_similarity_threshold: Optional[float] = 0.7
    limit: Optional[int] = 10


class OpportunityFitAnalysisSchema(Schema):
    """Detailed analysis of opportunity fit for a candidate."""
    profile_id: str
    opportunity_id: str
    role_title: str
    company_name: str
    fit_analysis: dict  # Contains structured_match, semantic_similarity, combined_score, llm_assessment_score, llm_reasoning
    skill_gap_analysis: Optional[dict]
    experience_relevance: Optional[dict]


@evaluations_router.get("/", response=List[EvaluationSetSchema], tags=["Evaluations"])
async def list_evaluation_sets(request):
    """List all evaluation sets."""
    from asgiref.sync import sync_to_async

    evaluation_sets = await sync_to_async(list)(
        EvaluationSet.objects.all().prefetch_related(
            'evaluations__profile', 'evaluations__opportunity', 'evaluations__opportunity__organisation'
        ).select_related('profile', 'opportunity')
    )
    return [
        EvaluationSetSchema(
            id=str(eval_set.id),
            evaluator_perspective=eval_set.evaluator_perspective,
            opportunity_id=str(eval_set.opportunity.id) if eval_set.opportunity else None,
            profile_id=str(eval_set.profile.id) if eval_set.profile else None,
            total_evaluated=eval_set.total_evaluated,
            llm_judged_count=eval_set.llm_judged_count,
            is_complete=eval_set.is_complete,
            evaluations=[
                EvaluationSchema(
                    id=str(eval.id),
                    profile_id=str(eval.profile.id),
                    opportunity_id=str(eval.opportunity.id),
                    opportunity_title=eval.opportunity.title,
                    opportunity_organisation_name=eval.opportunity.organisation.name,
                    candidate_name=f"{eval.profile.first_name} {eval.profile.last_name}" if eval_set.evaluator_perspective == 'employer' else None,
                    final_score=eval.final_score,
                    rank_in_set=eval.rank_in_set,
                    was_llm_judged=eval.was_llm_judged,
                    llm_reasoning=eval.llm_reasoning,
                    structured_score=eval.component_scores.get('structured', 0),
                    semantic_score=eval.component_scores.get('semantic', 0)
                )
                for eval in eval_set.evaluations.all()
            ]
        )
        for eval_set in evaluation_sets
    ]


@evaluations_router.get("/{evaluation_set_id}", response=EvaluationSetSchema, tags=["Evaluations"])
async def get_evaluation_set(request, evaluation_set_id: str):
    """Get a specific evaluation set by ID."""
    from asgiref.sync import sync_to_async

    evaluation_set = await sync_to_async(
        EvaluationSet.objects.prefetch_related(
            'evaluations__profile', 'evaluations__opportunity', 'evaluations__opportunity__organisation'
        ).get
    )(id=evaluation_set_id)

    return EvaluationSetSchema(
        id=str(evaluation_set.id),
        evaluator_perspective=evaluation_set.evaluator_perspective,
        opportunity_id=str(evaluation_set.opportunity.id) if evaluation_set.opportunity else None,
        profile_id=str(evaluation_set.profile.id) if evaluation_set.profile else None,
        total_evaluated=evaluation_set.total_evaluated,
        llm_judged_count=evaluation_set.llm_judged_count,
        is_complete=evaluation_set.is_complete,
        evaluations=[
            EvaluationSchema(
                id=str(eval.id),
                profile_id=str(eval.profile.id),
                opportunity_id=str(eval.opportunity.id),
                opportunity_title=eval.opportunity.title,
                opportunity_organisation_name=eval.opportunity.organisation.name,
                candidate_name=f"{eval.profile.first_name} {eval.profile.last_name}" if evaluation_set.evaluator_perspective == 'employer' else None,
                final_score=eval.final_score,
                rank_in_set=eval.rank_in_set,
                was_llm_judged=eval.was_llm_judged,
                llm_reasoning=eval.llm_reasoning,
                structured_score=eval.component_scores.get('structured', 0),
                semantic_score=eval.component_scores.get('semantic', 0)
            )
            for eval in evaluation_set.evaluations.all()
        ]
    )


# ==============================
# Profile-Opportunity Matching
# ==============================

@evaluations_router.post("/profiles/{profile_id}/find-opportunities", response=MatchingResponseSchema, tags=["Matching"])
async def find_opportunities_for_profile(request, profile_id: str, payload: MatchingRequestSchema):
    """Find best job opportunities for a candidate profile."""
    from apps.evaluations.services import EvaluationService

    try:
        service = EvaluationService()
        result = await service.find_opportunities_for_profile_async(
            profile_id=profile_id,
            llm_similarity_threshold=payload.llm_similarity_threshold,
            limit=payload.limit
        )

        return MatchingResponseSchema(
            evaluation_set_id=result['evaluation_set_id'],
            profile_id=result['profile_id'],
            total_opportunities_evaluated=result['total_opportunities_evaluated'],
            llm_judged_count=result['llm_judged_count'],
            top_matches=[
                MatchResultSchema(
                    rank=match['rank'],
                    opportunity_id=match['opportunity_id'],
                    role_title=match['role_title'],
                    company_name=match['company_name'],
                    final_score=match['final_score'],
                    structured_score=match['structured_score'],
                    semantic_score=match['semantic_score'],
                    llm_score=match['llm_score'],
                    llm_reasoning=match['llm_reasoning'],
                    was_llm_judged=match['was_llm_judged']
                )
                for match in result['top_matches']
            ]
        )

    except Exception as e:
        # Return 400 for invalid profile_id or other errors
        from ninja import HttpError
        raise HttpError(400, f"Error finding opportunities: {str(e)}")


@evaluations_router.post("/opportunities/{opportunity_id}/find-candidates", response=MatchingResponseSchema, tags=["Matching"])
async def find_candidates_for_opportunity(request, opportunity_id: str, payload: MatchingRequestSchema):
    """Find best candidates for a job opportunity."""
    from apps.evaluations.services import EvaluationService

    try:
        service = EvaluationService()
        result = await service.find_candidates_for_opportunity_async(
            opportunity_id=opportunity_id,
            llm_similarity_threshold=payload.llm_similarity_threshold,
            limit=payload.limit
        )

        return MatchingResponseSchema(
            evaluation_set_id=result['evaluation_set_id'],
            profile_id=result['opportunity_id'],  # This is the opportunity ID, not profile ID (employer perspective)
            total_opportunities_evaluated=result['total_candidates_evaluated'],
            llm_judged_count=result['llm_judged_count'],
            top_matches=[
                MatchResultSchema(
                    rank=match['rank'],
                    opportunity_id=match['profile_id'],  # Profile ID of the candidate
                    role_title=match['candidate_name'],  # Candidate's name
                    company_name='',  # Not applicable for candidates
                    final_score=match['final_score'],
                    structured_score=match['structured_score'],
                    semantic_score=match['semantic_score'],
                    llm_score=match['llm_score'],
                    llm_reasoning=match['llm_reasoning'],
                    was_llm_judged=match['was_llm_judged']
                )
                for match in result['top_matches']
            ]
        )

    except Exception as e:
        from ninja import HttpError
        raise HttpError(400, f"Error finding candidates: {str(e)}")


@evaluations_router.get("/profiles/{profile_id}/opportunities/{opportunity_id}/fit-analysis", response=OpportunityFitAnalysisSchema, tags=["Matching"])
async def analyze_opportunity_fit(request, profile_id: str, opportunity_id: str):
    """Get detailed analysis of how well a profile fits an opportunity."""
    from apps.evaluations.services import EvaluationService

    try:
        service = EvaluationService()
        result = await service.analyze_opportunity_fit_async(
            profile_id=profile_id,
            opportunity_id=opportunity_id
        )

        return OpportunityFitAnalysisSchema(
            profile_id=result['profile_id'],
            opportunity_id=result['opportunity_id'],
            role_title=result['role_title'],
            company_name=result['company_name'],
            fit_analysis=result['fit_analysis'],
            skill_gap_analysis=result.get('skill_gap_analysis'),
            experience_relevance=result.get('experience_relevance')
        )

    except Exception as e:
        from ninja import HttpError
        raise HttpError(400, f"Error analyzing fit: {str(e)}")
