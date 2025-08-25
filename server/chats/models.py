from django.db import models
from polymorphic.models import PolymorphicModel


class Chat(models.Model):
    """
    A chat between a human and the BookedAI agent.
    """
    subject = models.CharField(
        max_length=255,
        help_text="BookedAI will create a subject for the chat based on the context of the conversation.",
        null=True
        )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time the chat was created.",
        )

    def __str__(self):
        return f"{self.subject} - {self.created_at}"
    

class Message(PolymorphicModel):
    """
    A message in a BookedAI chat.  Should not be used directly
    instead use HumanMessage or BookedAIMessage for creation of messages, however
    to query all messages then Message.objects.filter(chat=chat) can be used.
    """
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        )
    
    text = models.TextField(
        help_text="The text of the message.",
        )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        )   
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.chat.subject} - {self.text[:10]}"


class HumanMessage(Message):
    """
    A message from a human to the BookedAI agent.
    """
    pass


class BookedAIMessage(Message):
    """
    A message from the BookedAI agent to a human.
    """
    pass

