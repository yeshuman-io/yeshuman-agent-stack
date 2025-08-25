import pytest
from django.db.models import QuerySet

from chats.models import Chat, Message, HumanMessage, BookedAIMessage

pytestmark = pytest.mark.django_db

class TestChatModel:
    """Tests for the Chat model"""
    
    def test_create_chat(self):
        """Test that a Chat can be created"""
        chat = Chat.objects.create(subject="Test Chat")
        
        assert chat.id is not None
        assert chat.subject == "Test Chat"
        assert chat.created_at is not None
    
    def test_chat_str_method(self, chat):
        """Test the __str__ method of the Chat model"""
        assert str(chat) == f"Test Chat - {chat.created_at}"
    
    def test_chat_without_subject(self, chat_without_subject):
        """Test that a Chat can be created without a subject"""
        assert chat_without_subject.id is not None
        assert chat_without_subject.subject is None
        assert chat_without_subject.created_at is not None

class TestMessageModels:
    """Tests for the Message, HumanMessage, and BookedAIMessage models"""
    
    def test_create_human_message(self, chat, human_message):
        """Test that a HumanMessage can be created"""
        assert human_message.id is not None
        assert human_message.chat == chat
        assert human_message.text == "Test human message"
        assert human_message.created_at is not None
        
        # Verify polymorphic behavior
        retrieved = Message.objects.get(id=human_message.id)
        assert isinstance(retrieved, HumanMessage)
    
    def test_create_bookedai_message(self, chat, bookedai_message):
        """Test that a BookedAIMessage can be created"""
        assert bookedai_message.id is not None
        assert bookedai_message.chat == chat
        assert bookedai_message.text == "Test BookedAI response"
        assert bookedai_message.created_at is not None
        
        # Verify polymorphic behavior
        retrieved = Message.objects.get(id=bookedai_message.id)
        assert isinstance(retrieved, BookedAIMessage)
    
    def test_message_ordering(self, chat_with_messages):
        """Test that messages are ordered by created_at in descending order"""
        messages = Message.objects.filter(chat=chat_with_messages)
        
        # Messages should be in reverse order of creation (newest first)
        assert messages.count() == 4
        assert isinstance(messages[0], BookedAIMessage)
        assert messages[0].text == "BookedAI message 2"
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].text == "Human message 2"
        assert isinstance(messages[2], BookedAIMessage)
        assert messages[2].text == "BookedAI message 1"
        assert isinstance(messages[3], HumanMessage)
        assert messages[3].text == "Human message 1"
    
    def test_message_str_method(self, chat, human_message):
        """Test the __str__ method of the Message model"""
        long_message = HumanMessage.objects.create(
            chat=chat,
            text="This is a very long message that should be truncated in the __str__ method"
        )
        
        # The Message.__str__ method truncates to 10 characters
        assert str(long_message) == f"Test Chat - This is a "
    
    def test_message_polymorphic_query(self, chat_with_messages):
        """Test that polymorphic queries work correctly"""
        # Query all messages
        all_messages = Message.objects.filter(chat=chat_with_messages)
        assert all_messages.count() == 4
        
        # Query only human messages
        human_messages = HumanMessage.objects.filter(chat=chat_with_messages)
        assert human_messages.count() == 2
        
        # Query only bookedai messages
        bookedai_messages = BookedAIMessage.objects.filter(chat=chat_with_messages)
        assert bookedai_messages.count() == 2 