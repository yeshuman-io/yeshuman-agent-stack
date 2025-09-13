from django.db import models
from pgvector.django import VectorField
from apps.organisations.models import Organisation
from apps.skills.models import Skill
import uuid


class Opportunity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='opportunities')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} at {self.organisation}"


class OpportunitySkill(models.Model):
    """
    Junction model linking Opportunity to required/preferred Skills
    """
    REQUIREMENT_CHOICES = [
        ('required', 'Required'),
        ('preferred', 'Preferred'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='opportunity_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='opportunity_skills')
    
    requirement_type = models.CharField(max_length=20, choices=REQUIREMENT_CHOICES, default='required')
    
    # Semantic embedding for skill requirement with job context
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['opportunity', 'skill']
    
    def __str__(self):
        return f"{self.opportunity} - {self.skill} ({self.requirement_type})"
    
    def get_embedding_text(self):
        """Generate rich text for embedding with requirement context and job details"""
        job_context = f"{self.opportunity.title} at {self.opportunity.organisation.name}"
        description_snippet = self.opportunity.description[:150] + "..." if len(self.opportunity.description) > 150 else self.opportunity.description
        
        return f"{self.skill.name} ({self.requirement_type}) for {job_context}. {description_snippet}"
    
    def generate_embedding(self):
        """Generate and save embedding for this instance"""
        from apps.embeddings.services import EmbeddingService
        service = EmbeddingService()
        text = self.get_embedding_text()
        self.embedding = service.generate_embedding(text)
        self.save(update_fields=['embedding'])
    
    def ensure_embedding(self):
        """Generate embedding if it doesn't exist"""
        if not self.embedding:
            self.generate_embedding()


class OpportunityExperience(models.Model):
    """
    Experience requirements/preferences for an opportunity.
    Description field can be embedded for semantic matching.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='opportunity_experiences')
    
    description = models.TextField()
    
    # Semantic embedding for experience requirements
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.opportunity} - {self.description[:50]}..."
    
    def get_embedding_text(self):
        """Generate rich text for embedding with job context"""
        job_context = f"{self.opportunity.title} at {self.opportunity.organisation.name}"
        return f"Experience requirement for {job_context}: {self.description}"
    
    def generate_embedding(self):
        """Generate and save embedding for this instance"""
        from apps.embeddings.services import EmbeddingService
        service = EmbeddingService()
        text = self.get_embedding_text()
        self.embedding = service.generate_embedding(text)
        self.save(update_fields=['embedding'])
    
    def ensure_embedding(self):
        """Generate embedding if it doesn't exist"""
        if not self.embedding:
            self.generate_embedding()
