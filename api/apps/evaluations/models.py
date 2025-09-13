from django.db import models
from apps.profiles.models import Profile
from apps.opportunities.models import Opportunity
import uuid


class EvaluationSet(models.Model):
    """
    A set of evaluations created from a single search request.
    Either employer searching for candidates, or candidate searching for opportunities.
    """
    EVALUATOR_PERSPECTIVE_CHOICES = [
        ('employer', 'Employer searching for candidates'),
        ('candidate', 'Candidate searching for opportunities'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What triggered this evaluation set
    evaluator_perspective = models.CharField(max_length=20, choices=EVALUATOR_PERSPECTIVE_CHOICES)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='evaluation_sets', null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='evaluation_sets', null=True, blank=True)
    
    # Search metadata
    total_evaluated = models.IntegerField(help_text="Total profiles/opportunities evaluated")
    llm_judged_count = models.IntegerField(default=0, help_text="How many got LLM evaluation")
    llm_threshold_percent = models.FloatField(default=0.2, help_text="Top % that get LLM judged (0.2 = 20%)")
    
    # Status
    is_complete = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['evaluator_perspective', 'created_at']),
            models.Index(fields=['is_complete']),
        ]
    
    def __str__(self):
        if self.evaluator_perspective == 'employer':
            return f"🏢 Candidates for {self.opportunity} ({self.total_evaluated} evaluated)"
        else:
            return f"👤 Opportunities for {self.profile} ({self.total_evaluated} evaluated)"


class Evaluation(models.Model):
    """
    Single evaluation result within an EvaluationSet.
    Records how well one Profile matches one Opportunity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Belongs to an evaluation set
    evaluation_set = models.ForeignKey(EvaluationSet, on_delete=models.CASCADE, related_name='evaluations')
    
    # The specific pairing being evaluated
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='evaluations')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='evaluations')
    
    # Results
    final_score = models.FloatField(help_text="Final evaluation score (0.0-1.0)")
    rank_in_set = models.IntegerField(help_text="Ranking within this evaluation set")
    
    # Component scores from pipeline
    component_scores = models.JSONField(
        default=dict,
        help_text="Pipeline breakdown: {'structured': 0.8, 'semantic': 0.6, 'llm_judge': 0.9}"
    )
    
    # LLM Judge (only for top performers)
    was_llm_judged = models.BooleanField(default=False)
    llm_reasoning = models.TextField(blank=True, help_text="LLM explanation (if judged)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['evaluation_set', 'profile', 'opportunity']
        indexes = [
            models.Index(fields=['evaluation_set', 'rank_in_set']),
            models.Index(fields=['final_score']),
            models.Index(fields=['was_llm_judged']),
        ]
    
    def __str__(self):
        return f"#{self.rank_in_set}: {self.profile} ↔ {self.opportunity} ({self.final_score:.2f})"
    
    @property
    def made_llm_cut(self):
        """Did this evaluation make it to LLM judging?"""
        return self.was_llm_judged
