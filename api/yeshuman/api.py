"""
Main API routes using Django Ninja.
"""
import os
from ninja import NinjaAPI, Schema
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.graph import ainvoke_agent, ainvoke_agent_sync, astream_agent_tokens
from auth.api import auth_router
from utils.sse import SSEHttpResponse
from streaming.generators import AnthropicSSEGenerator
from threads.services import (
    get_user_threads,
    get_thread,
    get_or_create_thread,
    get_all_thread_messages,
    get_thread_messages_as_langchain,
    create_human_message,
    create_assistant_message
)
from threads.models import Thread, Message, HumanMessage, AssistantMessage
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async

User = get_user_model()


async def get_user_from_token(request):
    """Extract and validate JWT token from request."""
    auth_header = request.headers.get('authorization', '')
    if not auth_header.startswith('Bearer '):
        return AnonymousUser()

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if user_id:
            try:
                return await sync_to_async(User.objects.get)(id=user_id)
            except User.DoesNotExist:
                pass
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
        pass

    return AnonymousUser()


# Initialize the API
api = NinjaAPI(
    title="Yes Human Agent API",
    version="1.0.0",
    description="API for Yes Human Agent Stack with MCP and A2A support"
)

# Add auth router
api.add_router("/auth", auth_router, tags=["Authentication"])


# Schemas
class ChatRequest(Schema):
    message: str
    session_id: Optional[str] = None


class ChatResponse(Schema):
    success: bool
    response: str
    session_id: Optional[str] = None
    error: Optional[str] = None


# Thread schemas
class ThreadResponse(Schema):
    id: str
    subject: Optional[str]
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageResponse(Schema):
    id: int
    text: str
    created_at: datetime
    message_type: str  # 'human', 'assistant', 'system', 'tool'


class ThreadDetailResponse(Schema):
    id: str
    subject: Optional[str]
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]


class CreateThreadRequest(Schema):
    subject: Optional[str] = None
    message: Optional[str] = None  # Optional initial message


class SendMessageRequest(Schema):
    message: str
    stream: bool = False  # Whether to stream the response


class HealthResponse(Schema):
    status: str
    version: str
    agent_ready: bool


class A2ARequest(Schema):
    agent_id: str
    message: str
    context: Optional[Dict[str, Any]] = {}


class A2AResponse(Schema):
    success: bool
    response: str
    agent_id: str
    error: Optional[str] = None


# Health check endpoint
@api.get("/health", response=HealthResponse)
def health_check(request):
    """Health check endpoint."""
    agent_ready = True
    try:
        # Test if we can create the agent
        create_agent()
    except Exception:
        agent_ready = False
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agent_ready": agent_ready
    }


# Chat endpoint
@api.post("/chat", response=ChatResponse)
async def chat(request, payload: ChatRequest):
    """Chat with the Yes Human agent."""
    try:
        result = await ainvoke_agent(payload.message)
        
        return ChatResponse(
            success=result["success"],
            response=result["response"],
            session_id=payload.session_id,
            error=result.get("error")
        )
    except Exception as e:
        return ChatResponse(
            success=False,
            response="Sorry, I encountered an error processing your request.",
            session_id=payload.session_id,
            error=str(e)
        )


# MCP endpoints are handled by the dedicated MCP API at /mcp/
# See mcp/api.py for full MCP protocol implementation


# A2A endpoints are handled by the dedicated A2A API at /a2a/
# See a2a/api.py for full Agent-to-Agent protocol implementation
# This endpoint remains for simple A2A message integration with the main agent

@api.post("/a2a/simple", response=A2AResponse)
async def simple_a2a_handler(request, payload: A2ARequest):
    """Simple A2A message handler that integrates with the main agent."""
    try:
        # Format message with agent context
        formatted_message = f"Message from agent '{payload.agent_id}': {payload.message}"
        if payload.context:
            formatted_message += f"\nContext: {payload.context}"
        
        result = await ainvoke_agent(formatted_message)
        
        return A2AResponse(
            success=result["success"],
            response=result["response"],
            agent_id=payload.agent_id,
            error=result.get("error")
        )
    
    except Exception as e:
        return A2AResponse(
            success=False,
            response="Error processing A2A request",
            agent_id=payload.agent_id,
            error=str(e)
        )


# Thread endpoints
@api.get("/threads", response=List[ThreadResponse], tags=["Threads"])
async def list_threads(request):
    """List all threads for the authenticated user."""
    user = await get_user_from_token(request)
    if not user or user.is_anonymous:
        return []  # Return empty list for unauthenticated users

    threads = await get_user_threads(str(user.id))
    return [
        ThreadResponse(
            id=str(thread.id),
            subject=thread.subject,
            user_id=thread.user_id,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            message_count=await get_all_thread_messages(thread.id, count_only=True)
        )
        for thread in threads
    ]


@api.get("/threads/{thread_id}", response=ThreadDetailResponse, tags=["Threads"])
async def get_thread_detail(request, thread_id: str):
    """Get a specific thread with all its messages."""
    user = await get_user_from_token(request)
    thread = await get_thread(thread_id)

    if not thread:
        from ninja import HttpError
        raise HttpError(404, "Thread not found")

    # Check if user owns this thread (if authenticated)
    if user and not user.is_anonymous and thread.user_id and thread.user_id != str(user.id):
        from ninja import HttpError
        raise HttpError(403, "Access denied")

    messages = await get_all_thread_messages(thread_id)
    message_responses = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            msg_type = "human"
        elif isinstance(msg, AssistantMessage):
            msg_type = "assistant"
        else:
            msg_type = "system"

        message_responses.append(MessageResponse(
            id=msg.id,
            text=msg.text,
            created_at=msg.created_at,
            message_type=msg_type
        ))

    return ThreadDetailResponse(
        id=str(thread.id),
        subject=thread.subject,
        user_id=thread.user_id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        messages=message_responses
    )


@api.post("/threads", response=ThreadResponse, tags=["Threads"])
async def create_thread(request, payload: CreateThreadRequest):
    """Create a new thread."""
    user = await get_user_from_token(request)

    # Create the thread
    thread = await get_or_create_thread(str(user.id) if user and not user.is_anonymous else None, payload.subject)

    # If initial message provided, create it
    if payload.message:
        await create_human_message(thread.id, payload.message)

        # Generate AI response using the agent
        try:
            messages = await get_thread_messages_as_langchain(thread.id)
            result = await ainvoke_agent_sync(payload.message, messages)

            # Extract the last AI message from the result
            if result and "messages" in result:
                ai_messages = [msg for msg in result["messages"] if msg.type == "ai"]
                if ai_messages:
                    ai_response = ai_messages[-1].content
                    await create_assistant_message(thread.id, ai_response)
        except Exception as e:
            # If agent fails, still create the thread but log error
            print(f"Agent error for thread {thread.id}: {e}")

    return ThreadResponse(
        id=str(thread.id),
        subject=thread.subject,
        user_id=thread.user_id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        message_count=await get_all_thread_messages(thread.id, count_only=True)
    )


@api.post("/threads/{thread_id}/messages", response=dict, tags=["Threads"])
async def send_message(request, thread_id: str, payload: SendMessageRequest):
    """Send a message to a thread and get AI response."""
    user = await get_user_from_token(request)
    thread = await get_thread(thread_id)

    if not thread:
        from ninja import HttpError
        raise HttpError(404, "Thread not found")

    # Check if user owns this thread (if authenticated)
    if user and not user.is_anonymous and thread.user_id and thread.user_id != str(user.id):
        from ninja import HttpError
        raise HttpError(403, "Access denied")

    # Create human message
    await create_human_message(thread_id, payload.message)

    # Handle streaming vs non-streaming responses
    if payload.stream:
        # Streaming response - use SSE
        try:
            messages = await get_thread_messages_as_langchain(thread_id)

            # Create streaming generator with accumulation
            async def thread_stream_generator():
                accumulated_response = []

                async for chunk in astream_agent_tokens(payload.message, messages):
                    # Accumulate message content for saving to thread
                    if chunk.get("type") == "message" and chunk.get("content"):
                        accumulated_response.append(chunk["content"])

                    yield chunk

            # Use AnthropicSSEGenerator to convert to SSE events
            sse_generator = AnthropicSSEGenerator()
            response = SSEHttpResponse(sse_generator.generate_sse(thread_stream_generator()))

            # Note: Saving to thread happens after streaming completes
            # This is a limitation of SSE - we can't await after the response starts
            # The frontend would need to call a separate endpoint to save or we use WebSockets

            return response

        except Exception as e:
            # Return error as SSE stream
            async def error_stream():
                yield {"type": "error", "content": f"Streaming error: {str(e)}"}
            sse_generator = AnthropicSSEGenerator()
            response = SSEHttpResponse(sse_generator.generate_sse(error_stream()))
            return response
    else:
        # Non-streaming response - complete response at once
        try:
            messages = await get_thread_messages_as_langchain(thread_id)
            result = await ainvoke_agent_sync(payload.message, messages)

            # Extract the last AI message from the result
            if result and "messages" in result:
                ai_messages = [msg for msg in result["messages"] if msg.type == "ai"]
                if ai_messages:
                    ai_response = ai_messages[-1].content
                    await create_assistant_message(thread_id, ai_response)
                    return {
                        "success": True,
                        "response": ai_response,
                        "thread_id": thread_id
                    }

            return {
                "success": False,
                "error": "No AI response generated",
                "thread_id": thread_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id
            }


@api.get("/threads/{thread_id}/messages", response=List[dict], tags=["Threads"])
async def get_thread_messages(request, thread_id: str):
    """Get all messages for a thread."""
    user = await get_user_from_token(request)
    thread = await get_thread(thread_id)

    if not thread:
        from ninja import HttpError
        raise HttpError(404, "Thread not found")

    # Check if user owns this thread (if authenticated)
    if user and not user.is_anonymous and thread.user_id and thread.user_id != str(user.id):
        from ninja import HttpError
        raise HttpError(403, "Access denied")

    # Get all messages for the thread
    messages = await get_all_thread_messages(thread_id)

    # Convert to response format
    message_list = []
    for msg in messages:
        # Determine message type based on class name
        if isinstance(msg, HumanMessage):
            message_type = "human"
        elif isinstance(msg, AssistantMessage):
            message_type = "assistant"
        elif isinstance(msg, SystemMessage):
            message_type = "system"
        elif isinstance(msg, ToolMessage):
            message_type = "tool"
        else:
            message_type = "unknown"

        message_list.append({
            "id": str(msg.id),
            "message_type": message_type,
            "text": msg.text,
            "created_at": msg.created_at,
            "thread_id": str(msg.thread_id)
        })

    return message_list


@api.delete("/threads/{thread_id}", tags=["Threads"])
async def delete_thread(request, thread_id: str):
    """Delete a thread."""
    user = await get_user_from_token(request)
    thread = await get_thread(thread_id)

    if not thread:
        from ninja import HttpError
        raise HttpError(404, "Thread not found")

    # Check if user owns this thread (if authenticated)
    if user and not user.is_anonymous and thread.user_id and thread.user_id != str(user.id):
        from ninja import HttpError
        raise HttpError(403, "Access denied")

    # Django CASCADE is already configured in the models:
    # Message.thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    #
    # However, Django Polymorphic models have additional FK constraints
    # between the base Message table and child tables. We need to handle
    # the polymorphic deletion carefully.

    # Option 1: Let Django handle CASCADE (may work if FK constraints are set up properly)
    # await thread.adelete()

    # Option 2: Manual cascade deletion (current working approach)
    from threads.services import get_all_thread_messages
    messages = await get_all_thread_messages(thread_id)
    for message in messages:
        await sync_to_async(message.delete)()

    # Now delete the thread
    await thread.adelete()
    return {"success": True, "message": "Thread deleted"}


# Test endpoint for development
@api.get("/test")
async def test_agent(request):
    """Test endpoint to verify agent functionality."""
    try:
        result = await ainvoke_agent("Hello! Can you calculate 2 + 2 for me?")
        return {"test_result": result}
    except Exception as e:
        return {"error": str(e)}
