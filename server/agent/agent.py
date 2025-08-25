import logging
import json
from typing import AsyncGenerator, Dict, Any, Optional, Tuple

from .graphs import async_graph_streaming_response
from .generators import SSEGenerator

from chats.models import Chat, HumanMessage, BookedAIMessage
from chats.services import (
    create_human_message, 
    create_bookedai_message,
    get_or_create_chat
)

logger = logging.getLogger(__name__)

class BookedAI:
    """
    A controller and orchestrator agent for the BookedAI system.

    BookedAI serves as the central coordination point that may delegate tasks to specialized 
    sub-agents or graph-based workflows (using langgraph or pydantic-graph). This agent 
    provides a unified interface to the system's capabilities.

    The primary objective of this class is to offer a declarative interface that self-documents
    the capabilities of the BookedAI application. This makes the system architecture transparent
    and accessible to developers.

    While Django handles the HTTP request/response cycle, this class encapsulates the major
    verbs and nouns of our agentic system into a class-based, declarative definition. This
    approach clearly communicates to developers how components interact and what the core
    responsibilities of our framework are.
    """
    def __init__(self):
        pass

    async def handle_bookedai_message(self, message: str, chat_id: Optional[str] = None) -> BookedAIMessage:
        """
        Handle a bookedai message. Creates a new chat if chat_id is None or empty.

        Args:
            message: The message to handle
            chat_id: The ID of the chat to handle the message for, or None to create a new chat

        Returns:
            The created bookedai message object
        """
        return await create_bookedai_message(chat_id, message)

    async def handle_human_message(self, message: str, chat_id: Optional[str] = None) -> HumanMessage:
        """
        Handle a human message. Creates a new chat if chat_id is None or empty.
        
        If this is the first message in a new chat, the system will automatically
        generate a subject for the chat based on the message content.

        Args:
            message: The message to handle
            chat_id: The ID of the chat to handle the message for, or None to create a new chat

        Returns:
            The created human message object
        """
        return await create_human_message(chat_id, message)
    
    async def handle_new_bookedai_chat(self) -> Tuple[Chat, AsyncGenerator[bytes, None]]:
        """
        Handle a new bookedai chat. Creates a new chat and generates a welcome message.

        Returns:
            A tuple containing (chat, streaming_response) with the chat object
            and the streaming response generator
        """
        # Create a new chat
        chat_obj = await get_or_create_chat()
        
        # Create a system message to welcome the user
        system_message = "Welcome the user as BookedAI. Introduce yourself and explain how you can help."
        
        # Return the chat and streaming response generator
        return chat_obj, self.streaming_response(system_message=system_message, chat_id=chat_obj.id)


    async def streaming_response(
        self, 
        message_obj: Optional[object] = None, 
        system_message: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream and yield SSE events to the BookedAI client or labs via API endpoint.
        
        This method uses a graph-based routing system to determine whether to use:
        1. A simple one-shot streaming response, or
        2. A graph-based streaming response with thinking, message, and optional voice
        
        The response is formatted according to the Anthropic SSE specification.
        
        Args:
            message_obj: The message object to respond to by the streaming agent
                         (optional if system_message is provided)
            system_message: The system message to include in the streaming response
                           (required if message_obj is not provided)
            chat_id: The ID of the chat to save the response to
                     (required if message_obj is not provided)
        
        Returns:
            A generator function that yields SSE events in Anthropic format
            
        Raises:
            ValueError: If neither message_obj nor system_message is provided
        """
        # Validate that at least one parameter is provided
        if message_obj is None and not system_message:
            raise ValueError("Either message_obj or system_message must be provided")
            
        # Track the complete response to save later
        complete_message = ""
            
        # Create an SSEGenerator to format the response
        sse_generator = SSEGenerator()
        
        # Use the graph-based streaming response which includes routing logic
        stream_generator = async_graph_streaming_response(message_obj, system_message)
        
        # Process stream through SSE generator
        async for event in sse_generator.generate_sse(stream_generator):
            # Pass the event through to the client
            yield event
            
            # Try to extract message content for saving
            try:
                # Decode the event to analyze it
                event_str = event.decode('utf-8')
                if "data: " in event_str:
                    # Extract just the data part
                    data_str = event_str.split("data: ", 1)[1].strip()
                    # Parse the JSON
                    data = json.loads(data_str)
                    # If it's a message event, accumulate the content
                    if data.get("type") == "content_block_delta" and "delta" in data:
                        delta = data["delta"]
                        if delta.get("type") == "text_delta" and "text" in delta:
                            complete_message += delta["text"]
            except Exception as e:
                # Log but don't break the stream
                logger.error(f"Error extracting message content: {e}")
                
        # If we have accumulated a complete message, save it
        if complete_message:
            # Get chat_id either from message_obj or from the parameter
            message_chat_id = message_obj.chat.id if message_obj and hasattr(message_obj, 'chat') else chat_id
            
            # Ensure we have a chat_id to save to
            if message_chat_id:
                await self.handle_bookedai_message(message=complete_message, chat_id=message_chat_id)
            else:
                logger.error("No chat_id available to save BookedAI message")