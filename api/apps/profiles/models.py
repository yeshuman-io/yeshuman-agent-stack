from django.db import models
from pgvector.django import VectorField
from apps.organisations.models import Organisation
from apps.skills.models import Skill
import uuid


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    # Additional profile fields
    bio = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ProfileExperience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='profile_experiences')
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='profile_experiences')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Semantic embedding for experience description and context
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.profile} - {self.title} at {self.organisation}"
    
    def get_embedding_text(self):
        """Generate rich text for embedding with role context and skills used"""
        # Get skills demonstrated in this role
        skills_used = [pes.skill.name for pes in self.profile_experience_skills.all()]
        skills_text = f" Skills used: {', '.join(skills_used)}." if skills_used else ""
        
        # Format duration
        duration = f"from {self.start_date.year} to {'present' if not self.end_date else self.end_date.year}"
        
        return f"{self.title} at {self.organisation.name} ({duration}). {self.description}{skills_text}"
    
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


class ProfileSkill(models.Model):
    """
    Junction model linking Profile to Skills with evidence level
    """
    EVIDENCE_CHOICES = [
        ('stated', 'Stated Competency'),
        ('experienced', 'Experience-based'),
        ('evidenced', 'Evidenced Competency'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='profile_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='profile_skills')
    
    evidence_level = models.CharField(max_length=20, choices=EVIDENCE_CHOICES, default='stated')
    
    # Semantic embedding for skill with evidence and context
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['profile', 'skill']
    
    def __str__(self):
        return f"{self.profile} - {self.skill} ({self.evidence_level})"
    
    def get_embedding_text(self):
        """Generate rich text for embedding with evidence level and recent context"""
        # Find most recent experience using this skill (through ProfileExperienceSkill)
        from django.apps import apps
        ProfileExperienceSkill = apps.get_model('profiles', 'ProfileExperienceSkill')
        latest_experience_skill = ProfileExperienceSkill.objects.filter(
            skill=self.skill,
            profile_experience__profile=self.profile
        ).select_related('profile_experience', 'profile_experience__organisation').order_by('-profile_experience__end_date').first()
        
        if latest_experience_skill:
            exp = latest_experience_skill.profile_experience
            recency = "currently using" if not exp.end_date else f"used until {exp.end_date.year}"
            context = f" - {recency} at {exp.organisation.name} as {exp.title}"
            return f"{self.skill.name} ({self.evidence_level}){context}"
        else:
            return f"{self.skill.name} ({self.evidence_level}) - stated competency"
    
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


class ProfileExperienceSkill(models.Model):
    """
    Junction model linking ProfileExperience to Skills demonstrated in that role
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile_experience = models.ForeignKey(ProfileExperience, on_delete=models.CASCADE, related_name='profile_experience_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='profile_experience_skills')
    
    # Semantic embedding for skill-in-context with temporal relevance
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['profile_experience', 'skill']
    
    def __str__(self):
        return f"{self.profile_experience} - {self.skill}"
    
    def get_embedding_text(self):
        """Generate rich text for embedding with temporal and role context"""
        exp = self.profile_experience
        recency_status = "current role" if not exp.end_date else f"previous role until {exp.end_date.year}"
        
        # Include role context and experience description snippet
        description_snippet = exp.description[:200] + "..." if len(exp.description) > 200 else exp.description
        
        return f"{self.skill.name} - {recency_status} at {exp.organisation.name} as {exp.title}. {description_snippet}"
    
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
    
    def get_temporal_weight(self) -> float:
        """
        Calculate temporal weight for this skill-in-experience based on recency.
        Recent experience is weighted higher than older experience.
        """
        from apps.evaluations.temporal_weighting import calculate_combined_temporal_weight
        
        return calculate_combined_temporal_weight(
            self.profile_experience.start_date,
            self.profile_experience.end_date
        )
    
    def get_temporal_context(self) -> str:
        """Get human-readable temporal context for debugging"""
        from apps.evaluations.temporal_weighting import get_temporal_context_description
        
        return get_temporal_context_description(
            self.profile_experience.start_date,
            self.profile_experience.end_date
        )
