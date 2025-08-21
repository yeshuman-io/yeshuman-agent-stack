"""
A2A (Agent-to-Agent) Django models for data storage.
"""
import uuid
from django.db import models
from django.utils import timezone
from typing import Dict, Any, Optional


class Agent(models.Model):
    """Agent registry model."""
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('busy', 'Busy'),
        ('maintenance', 'Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Unique agent name")
    endpoint_url = models.URLField(max_length=500, blank=True, null=True, help_text="Agent's callback URL")
    capabilities = models.JSONField(default=list, help_text="List of agent capabilities")
    metadata = models.JSONField(default=dict, help_text="Additional agent metadata")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'a2a_agents'
        ordering = ['-last_seen']
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def is_online(self) -> bool:
        """Check if agent is currently online."""
        return self.status == 'online'
    
    def update_heartbeat(self):
        """Update the agent's last seen timestamp."""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])


class Conversation(models.Model):
    """Conversation thread between agents."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=255, blank=True, help_text="Conversation topic")
    participants = models.ManyToManyField(Agent, related_name='conversations')
    metadata = models.JSONField(default=dict, help_text="Conversation metadata")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'a2a_conversations'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation: {self.topic or str(self.id)[:8]}"


class A2AMessage(models.Model):
    """Message between agents."""
    
    MESSAGE_TYPES = [
        ('task', 'Task Assignment'),
        ('response', 'Task Response'),
        ('request', 'Information Request'),
        ('broadcast', 'Broadcast Message'),
        ('notification', 'Notification'),
        ('error', 'Error Message'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Normal'),
        (4, 'Low'),
        (5, 'Background'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Agent relationships
    from_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='sent_messages')
    to_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    
    # Message content
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='request')
    subject = models.CharField(max_length=255, blank=True, help_text="Message subject/title")
    payload = models.JSONField(help_text="Message content and data")
    
    # Message properties
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    
    # Response tracking
    response_required = models.BooleanField(default=False)
    response_timeout = models.DateTimeField(null=True, blank=True)
    response_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='original_message')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'a2a_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_agent', 'created_at']),
            models.Index(fields=['to_agent', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['conversation', 'created_at']),
        ]
    
    def __str__(self):
        to_agent_name = self.to_agent.name if self.to_agent else "broadcast"
        return f"{self.from_agent.name} -> {to_agent_name}: {self.message_type}"
    
    def mark_delivered(self):
        """Mark message as delivered."""
        if self.status == 'pending':
            self.status = 'delivered'
            self.delivered_at = timezone.now()
            self.save(update_fields=['status', 'delivered_at'])
    
    def mark_read(self):
        """Mark message as read."""
        if self.status in ['pending', 'delivered']:
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class Task(models.Model):
    """Task model for tracking agent tasks."""
    
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Task assignment
    created_by = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='created_tasks')
    assigned_to = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='assigned_tasks', null=True, blank=True)
    
    # Task content
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=50, default='general')
    parameters = models.JSONField(default=dict, help_text="Task parameters and configuration")
    
    # Task status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    result = models.JSONField(null=True, blank=True, help_text="Task result data")
    error_message = models.TextField(blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    # Related messages
    request_message = models.OneToOneField(A2AMessage, on_delete=models.CASCADE, related_name='task', null=True, blank=True)
    
    class Meta:
        db_table = 'a2a_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"Task: {self.title} ({self.status})"
    
    def assign_to(self, agent: Agent):
        """Assign task to an agent."""
        self.assigned_to = agent
        self.status = 'assigned'
        self.assigned_at = timezone.now()
        self.save(update_fields=['assigned_to', 'status', 'assigned_at'])
    
    def start(self):
        """Mark task as started."""
        if self.status == 'assigned':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])
    
    def complete(self, result: Optional[Dict[str, Any]] = None):
        """Mark task as completed."""
        self.status = 'completed'
        self.progress = 100
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save(update_fields=['status', 'progress', 'completed_at', 'result'])
    
    def fail(self, error_message: str):
        """Mark task as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])