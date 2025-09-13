from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid
from pgvector.django import VectorField


class Memory(models.Model):
    """
    General-purpose memory storage model for Mem0 clients.
    Domain-agnostic design - application logic determines usage patterns.
    """
    
    # Core Mem0 fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255, db_index=True)
    content = models.TextField(help_text="The actual memory content/text")
    
    # Vector embedding for semantic search (1536 dimensions for text-embedding-3-small)
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    # Mem0 memory type classification (from Mem0 documentation)
    memory_type = models.CharField(
        max_length=20,
        choices=[
            ('factual', 'Factual - Static information and preferences'),
            ('episodic', 'Episodic - Time-bound experiences and events'),
            ('semantic', 'Semantic - Patterns and insights derived from experiences'),
        ],
        default='factual',
        db_index=True
    )
    
    # Interaction classification (from Mem0 documentation)
    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ('conversation', 'Conversation - Direct user communication'),
            ('observation', 'Observation - System-observed patterns'),
            ('insight', 'Insight - Derived understanding or connections'),
        ],
        default='conversation',
        db_index=True
    )
    
    # Generic categorization (domain-agnostic)
    category = models.CharField(
        max_length=50, 
        db_index=True,
        help_text="General category (e.g., 'health', 'work', 'personal', 'finance')"
    )
    
    subcategory = models.CharField(
        max_length=50, 
        blank=True,
        db_index=True,
        help_text="Specific subcategory within the main category"
    )
    
    # Generic importance/priority
    importance = models.CharField(
        max_length=10,
        choices=[
            ('high', 'High priority'),
            ('medium', 'Medium priority'),
            ('low', 'Low priority'),
        ],
        default='medium',
        db_index=True
    )
    
    # Session and source tracking
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    source = models.CharField(max_length=50, default='mem0_client')
    
    # Generic flags
    requires_followup = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    
    # Flexible metadata for domain-specific data
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Domain-specific metadata (health_type, tags, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'memory_type']),
            models.Index(fields=['user_id', 'category']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['user_id', 'importance']),
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['category', 'subcategory']),
        ]
    
    def __str__(self):
        return f"{self.user_id}: {self.content[:50]}..." if len(self.content) > 50 else f"{self.user_id}: {self.content}"


class MemoryRelation(models.Model):
    """
    Store relationships between memories for pattern recognition.
    Domain-agnostic relationship tracking.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name='relations_from')
    to_memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name='relations_to')
    
    relation_type = models.CharField(
        max_length=20,
        choices=[
            ('related', 'Generally related'),
            ('causes', 'One memory causes another'),
            ('follows', 'Sequential relationship'),
            ('contradicts', 'Conflicting information'),
            ('confirms', 'Confirms or supports'),
            ('pattern', 'Part of a pattern'),
        ],
        default='related'
    )
    
    strength = models.FloatField(
        default=1.0,
        help_text="Relationship strength (0.0-1.0)"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['from_memory', 'to_memory', 'relation_type']
    
    def __str__(self):
        return f"{self.from_memory.content[:30]} -> {self.relation_type} -> {self.to_memory.content[:30]}"


class MemorySearch(models.Model):
    """
    Track memory searches for analytics and improving retrieval.
    Domain-agnostic search tracking.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255, db_index=True)
    query = models.TextField()
    query_embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    # Results and performance
    results_count = models.IntegerField(default=0)
    search_duration_ms = models.IntegerField(null=True, blank=True)
    
    # Context
    session_id = models.CharField(max_length=255, null=True, blank=True)
    search_type = models.CharField(
        max_length=20,
        choices=[
            ('semantic', 'Semantic similarity search'),
            ('keyword', 'Keyword-based search'),
            ('temporal', 'Time-based search'),
            ('category', 'Category-based search'),
        ],
        default='semantic'
    )
    
    # Analytics
    clicked_results = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Memory IDs that were clicked/used from this search"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user_id}: {self.query[:50]}..." if len(self.query) > 50 else f"{self.user_id}: {self.query}"


class MemoryPattern(models.Model):
    """
    Store discovered patterns in user data.
    Domain-agnostic pattern recognition.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255, db_index=True)
    
    pattern_type = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Type of pattern discovered (domain-specific)"
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    confidence = models.FloatField(
        default=0.5,
        help_text="Pattern confidence score (0.0-1.0)"
    )
    
    # Related memories that support this pattern
    supporting_memories = models.ManyToManyField(Memory, related_name='patterns')
    
    # Pattern data
    pattern_data = models.JSONField(
        default=dict,
        help_text="Structured data about the pattern (frequencies, correlations, etc.)"
    )
    
    # Category alignment
    category = models.CharField(max_length=50, blank=True, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-confidence', '-last_updated']
        indexes = [
            models.Index(fields=['user_id', 'pattern_type']),
            models.Index(fields=['user_id', 'confidence']),
            models.Index(fields=['is_active', 'confidence']),
            models.Index(fields=['category', 'pattern_type']),
        ]
    
    def __str__(self):
        return f"{self.user_id}: {self.title} ({self.confidence:.2f})" 