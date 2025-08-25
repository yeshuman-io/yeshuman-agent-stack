#!/usr/bin/env python
"""
BookedAI Instructors Module

This module implements streaming text responses using the Instructor library
for different types of tasks (thinking, message, voice). Each instructor
is focused on a specific type of response and can use any supported model provider.
"""
from typing import AsyncIterator, Optional, Literal, TypeVar, Generic, Dict, Any, AsyncGenerator
import instructor
from instructor import Mode
from instructor.dsl.partial import PartialLiteralMixin
from openai import AsyncOpenAI, APIError, APIConnectionError, AuthenticationError, RateLimitError
from anthropic import AsyncAnthropic, APIError as AnthropicAPIError, APIConnectionError as AnthropicConnectionError, AuthenticationError as AnthropicAuthError
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import json

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class ThinkingResponse(BaseModel, PartialLiteralMixin):
    """Model for analytical thinking responses."""
    thinking: str = Field(..., description="Step-by-step reasoning process")
    next_action: Optional[Literal["voice", "message", "voice_and_message", "complete"]] = Field(
        default=None,
        description="Recommended next action: 'voice', 'message', 'voice_and_message', or 'complete'"
    )

    def __init__(self, **data):
        super().__init__(**data)
        # If thinking contains a next_action line, extract it
        if "next_action:" in self.thinking.lower():
            action_text = self.thinking.lower().split("next_action:")[1].strip()
            if action_text in ["voice", "message", "voice_and_message", "complete"]:
                self.next_action = action_text
                # Remove the next_action line from thinking
                self.thinking = self.thinking.split("next_action:")[0].strip()


class MessageResponse(BaseModel):
    """Model for detailed text responses."""
    text: str = Field(..., description="Detailed text response")


class VoiceResponse(BaseModel):
    """Model for voice-optimized responses."""
    text: str = Field(..., description="Voice-optimized text")


# -----------------------------------------------------------------------------
# Base Instructor
# -----------------------------------------------------------------------------

T = TypeVar('T', bound=BaseModel)

class BaseInstructor(Generic[T]):
    """Base class for all instructors."""
    
    def __init__(self, model_name: str, system_prompt: str, response_model: type[T]):
        """
        Initialize the base instructor.
        
        Args:
            model_name: The model to use
            system_prompt: The system prompt for the model
            response_model: The Pydantic model type for structured responses
        """
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.response_model = response_model
        self.client = None
    
    async def generate(self, query: str) -> AsyncIterator[T]:
        """
        Generate a streaming response.
        
        Args:
            query: The input query
            
        Yields:
            Structured response objects
        """
        raise NotImplementedError("Subclasses must implement generate()")


class ThinkingInstructor(BaseInstructor[ThinkingResponse]):
    """
    Instructor for analytical thinking and decision-making.
    Uses OpenAI's GPT-4 for high-intelligence analysis.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the thinking instructor.
        
        Args:
            model_name: The model to use, defaults to GPT-4
        """
        model = model_name or os.environ.get("THINKING_MODEL", "gpt-4-1106-preview")
        system_prompt = """
        You are a thinking & orchestration agent/node for BookedAI an AI Travel Agent.

        You're role is to delegate to other agents/nodes whilst providing thoughts outloud that will be
        noted by the user.
        
        Be concise.

        Take note of the change of state by the other agents/nodes in order to bring the graph state response
        to completion.
        
        On the last line of your response, write only "next_action: voice", "next_action: message", 
        "next_action: voice_and_message", or "next_action: complete" based on your recommendation.
        
        For the next_action field, choose:
        - "voice": A quick acknowledgment of the user's request, especially if tool calling is required (not implemented yet)
        - "message": A final detailed response to the user
        - "voice_and_message": If no tool calling respond using voice and message in parallel, then complete.
        - "complete": After the message response has been delivered

        If the message or parallel execution has already been completed, simply acknowledge completion
        with a brief message like "Response completed successfully" and set next_action to "complete".
        """
        super().__init__(model, system_prompt, ThinkingResponse)
        
        # Create client directly (without instructor patch)
        try:
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("No API key provided for OpenAI")
                raise ValueError("No API key provided for OpenAI")
                
            # Create a regular OpenAI client for raw streaming
            self.client = AsyncOpenAI(api_key=openai_api_key)
            logger.info("Successfully initialized OpenAI client for raw streaming")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            raise
    
    async def generate(
        self, 
        query: str,
        message_executed: bool = False,
        parallel_executed: bool = False
    ) -> AsyncGenerator[ThinkingResponse, None]:
        """
        Generate a thinking response for the given query.
        
        Args:
            query: The query to think about
            message_executed: Whether the message node has been executed
            parallel_executed: Whether the parallel node has been executed
            
        Yields:
            ThinkingResponse objects with thinking content and next_action
        """
        logger.info(f"ThinkingInstructor: Generating response for query: {query[:50]}...")
        
        # If we've already completed the main response, just acknowledge completion
        if message_executed or parallel_executed:
            logger.info("ThinkingInstructor: Main response already executed, generating completion message")
            yield ThinkingResponse(
                thinking="Response completed successfully.",
                next_action="complete"
            )
            return
            
        # Use raw streaming for more granular updates
        logger.info(f"ThinkingInstructor: Using model: {self.model_name}")
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": query}
            ],
            stream=True,
            temperature=0.2
        )
        
        logger.info("ThinkingInstructor: Starting to process stream...")
        
        # Track the complete thinking and final next_action
        current_text = ""
        final_next_action = None
        
        # Process the streaming response
        async for chunk in response:
            if chunk.choices[0].delta.content:
                new_content = chunk.choices[0].delta.content
                current_text += new_content
                
                # Check for next_action in the new content
                if "next_action:" in new_content.lower():
                    action_line = new_content.lower().split("next_action:")[1].split("\n")[0].strip()
                    final_next_action = action_line
                
                # Yield each chunk with the current thinking
                yield ThinkingResponse(
                    thinking=new_content,
                    next_action=None  # Don't set next_action until final chunk
                )
        
        # After processing all chunks, yield a final response with the complete thinking
        # and the final next_action
        yield ThinkingResponse(
            thinking=current_text,
            next_action=final_next_action
        )
        
        logger.info(f"ThinkingInstructor: Stream complete. Total thinking length={len(current_text)}, final next_action={final_next_action}")
        logger.info(f"ThinkingInstructor: Complete thinking: {current_text}")


class MessageInstructor(BaseInstructor[MessageResponse]):
    """
    Instructor for detailed message responses.
    Uses Anthropic's Claude for high-quality, detailed responses.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the message instructor.
        
        Args:
            model_name: The model to use, defaults to Claude 3 Haiku
        """
        model = model_name or os.environ.get("MESSAGE_MODEL", "claude-3-haiku-20240307")
        system_prompt = """
        You are a message response agent that provides detailed
        and helpful information in a clear and engaging way.
        """
        super().__init__(model, system_prompt, MessageResponse)
        
        # Create client directly
        try:
            anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                logger.error("No API key provided for Anthropic")
                raise ValueError("No API key provided for Anthropic")
                
            # Create a regular Anthropic client for raw streaming
            self.client = AsyncAnthropic(api_key=anthropic_api_key)
            logger.info("Successfully initialized Anthropic client with Instructor")
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {e}")
            raise
    
    async def generate(self, query: str) -> AsyncIterator[MessageResponse]:
        """Generate a streaming message response."""
        try:
            # Use messages.create with stream=True for raw streaming
            stream_response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=1000,  # Reduced from 4096 to stay within rate limits
                system=self.system_prompt,  # System prompt as top-level parameter
                messages=[
                    {"role": "user", "content": query}
                ],
                stream=True
            )
            
            logger.info(f"MessageInstructor: Starting stream for query: {query[:50]}...")
            
            current_text = ""
            
            # Process the streaming response
            async for chunk in stream_response:
                if chunk.type == 'content_block_delta' and chunk.delta.text:
                    current_text += chunk.delta.text
                    yield MessageResponse(text=chunk.delta.text)
            
            # Log summary after stream processing is complete
            logger.info(f"MessageInstructor: Stream complete. Total text length={len(current_text)}")
            logger.info(f"MessageInstructor: Complete text: {current_text}")
                    
        except Exception as e:
            logger.error(f"Error in message instructor: {e}")
            logger.exception("Full traceback:")
            yield MessageResponse(text=f"Error generating response: {str(e)}")


class VoiceInstructor(BaseInstructor[VoiceResponse]):
    """
    Instructor for voice-optimized responses.
    Uses Groq's LLaMA2 for fast, concise responses.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the voice instructor.
        
        Args:
            model_name: The model to use, defaults to Llama 3.1 8B Instant
        """
        model = model_name or os.environ.get("VOICE_MODEL", "llama-3.1-8b-instant")
        system_prompt = """
        You are a voice response agent for BookedAI, an AI Travel Agent.
        Provide concise, clear, and natural-sounding responses optimized for speech.
        Focus on travel-related topics like:
        - Flight bookings and travel arrangements
        - Hotel accommodations and amenities
        - Car rentals and transportation
        - Travel tips and destination information
        - Itinerary planning and travel logistics
        
        Keep responses brief and conversational, as if speaking directly to a traveler.
        Use a friendly, professional tone that's appropriate for a travel agent.
        """
        super().__init__(model, system_prompt, VoiceResponse)
        
        # Create client directly
        try:
            groq_api_key = os.environ.get("GROQ_API_KEY")
            if not groq_api_key:
                logger.error("No API key provided for Groq")
                raise ValueError("No API key provided for Groq")
                
            # Create a patched OpenAI-compatible client for Groq
            client = AsyncOpenAI(
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            self.client = instructor.patch(client, mode=Mode.TOOLS)
            logger.info("Successfully initialized Groq client with Instructor")
        except Exception as e:
            logger.error(f"Error initializing Groq client: {e}")
            raise
    
    async def generate(self, query: str) -> AsyncIterator[VoiceResponse]:
        """Generate a streaming voice response."""
        try:
            logger.info(f"VoiceInstructor: Generating response for query: {query[:50]}...")
            logger.info("VoiceInstructor: Starting to process stream...")
            
            # Use create with stream=True since Groq doesn't support create_partial
            stream_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                stream=True
            )
            
            # Await the coroutine properly before attempting to iterate
            response = await stream_response
            
            current_text = ""
            
            # Process the streaming response
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    current_text += chunk.choices[0].delta.content
                    yield VoiceResponse(text=chunk.choices[0].delta.content)
            
            # Log summary after stream processing is complete
            logger.info(f"VoiceInstructor: Stream complete. Total text length={len(current_text)}")
            logger.info(f"VoiceInstructor: Complete text: {current_text}")
                    
        except Exception as e:
            logger.error(f"Error in voice instructor: {e}")
            logger.exception("Full traceback:")
            # Return multiple chunks to simulate streaming
            yield VoiceResponse(text="Error: ")
            yield VoiceResponse(text=f"Error generating response: {str(e)}")


def create_instructor(task_type: Literal["thinking", "message", "voice"], model_name: Optional[str] = None):
    """
    Factory function to create the appropriate instructor.
    
    Args:
        task_type: The type of task ("thinking", "message", or "voice")
        model_name: Optional model name override
        
    Returns:
        An instance of the appropriate instructor
    """
    if task_type == "thinking":
        return ThinkingInstructor(model_name)
    elif task_type == "message":
        return MessageInstructor(model_name)
    elif task_type == "voice":
        return VoiceInstructor(model_name)
    else:
        raise ValueError(f"Invalid task type: {task_type}") 