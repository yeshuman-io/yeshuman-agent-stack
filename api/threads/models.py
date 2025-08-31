from django.db import models
from polymorphic.models import PolymorphicModel


class Thread(models.Model):
    """
    A conversation thread between a human and the Yes Human agent.
    """
    subject = models.CharField(
        max_length=255,
        help_text="Yes Human will create a subject for the thread based on the context of the conversation.",
        null=True,
        blank=True
    )
    user_id = models.CharField(
        max_length=100,
        help_text="ID of the user who owns this thread",
        null=True,
        blank=True
    )
    session_id = models.CharField(
        max_length=100,
        help_text="Session ID for anonymous users",
        null=True,
        blank=True
    )
    is_anonymous = models.BooleanField(
        default=False,
        help_text="Whether this thread belongs to an anonymous user"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time the thread was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The date and time the thread was last updated.",
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.subject or 'Untitled'} - {self.created_at}"


class Message(PolymorphicModel):
    """
    A message in a Yes Human conversation thread. Should not be used directly.
    Instead use HumanMessage or AssistantMessage for creation of messages, however
    to query all messages then Message.objects.filter(thread=thread) can be used.
    """
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
    )

    text = models.TextField(
        help_text="The text content of the message.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    # Store additional metadata for streaming content
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata like voice content, tool calls, etc.",
        blank=True
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.thread.subject or 'Untitled'} - {self.text[:50]}"


class HumanMessage(Message):
    """
    A message from a human to the Yes Human agent.
    """
    pass


class AssistantMessage(Message):
    """
    A message from the Yes Human agent to a human.
    """
    pass


class SystemMessage(Message):
    """
    A system message in the conversation thread.
    """
    pass


class ToolMessage(Message):
    """
    A message containing tool execution results.
    """
    tool_name = models.CharField(
        max_length=100,
        help_text="Name of the tool that was executed",
        blank=True
    )
    tool_result = models.JSONField(
        default=dict,
        help_text="Result of the tool execution",
        blank=True
    )
