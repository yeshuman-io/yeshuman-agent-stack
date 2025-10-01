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
    final_score: float
    rank_in_set: int
    was_llm_judged: bool
    llm_reasoning: Optional[str]


class EvaluationSetSchema(Schema):
    """Schema for EvaluationSet model."""
    id: str
    evaluator_perspective: str
    total_evaluated: int
    llm_judged_count: int
    is_complete: bool
    evaluations: List[EvaluationSchema]


@evaluations_router.get("/", response=List[EvaluationSetSchema], tags=["Evaluations"])
async def list_evaluation_sets(request):
    """List all evaluation sets."""
    from asgiref.sync import sync_to_async

    evaluation_sets = await sync_to_async(list)(EvaluationSet.objects.all().prefetch_related('evaluations'))
    return [
        EvaluationSetSchema(
            id=str(eval_set.id),
            evaluator_perspective=eval_set.evaluator_perspective,
            total_evaluated=eval_set.total_evaluated,
            llm_judged_count=eval_set.llm_judged_count,
            is_complete=eval_set.is_complete,
            evaluations=[
                EvaluationSchema(
                    id=str(eval.id),
                    profile_id=str(eval.profile.id),
                    opportunity_id=str(eval.opportunity.id),
                    final_score=eval.final_score,
                    rank_in_set=eval.rank_in_set,
                    was_llm_judged=eval.was_llm_judged,
                    llm_reasoning=eval.llm_reasoning
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

    evaluation_set = await sync_to_async(EvaluationSet.objects.prefetch_related('evaluations').get)(id=evaluation_set_id)
    return EvaluationSetSchema(
        id=str(evaluation_set.id),
        evaluator_perspective=evaluation_set.evaluator_perspective,
        total_evaluated=evaluation_set.total_evaluated,
        llm_judged_count=evaluation_set.llm_judged_count,
        is_complete=evaluation_set.is_complete,
        evaluations=[
            EvaluationSchema(
                id=str(eval.id),
                profile_id=str(eval.profile.id),
                opportunity_id=str(eval.opportunity.id),
                final_score=eval.final_score,
                rank_in_set=eval.rank_in_set,
                was_llm_judged=eval.was_llm_judged,
                llm_reasoning=eval.llm_reasoning
            )
            for eval in evaluation_set.evaluations.all()
        ]
    )
