"""
Agent API endpoints for custom UI consumers.

This module provides a unified streaming endpoint that returns Anthropic-compatible
SSE streams for custom UIs expecting delta events. Follows the server/ pattern.
"""
import json
import logging
from typing import Optional
from ninja import NinjaAPI
from pydantic import BaseModel

from utils.sse import SSEHttpResponse
from streaming.generators import AnthropicSSEGenerator
from agent.graph import astream_agent_tokens

logger = logging.getLogger(__name__)

agent_api = NinjaAPI(urls_namespace="agent")


class AgentRequest(BaseModel):
    """Request model for agent interactions."""
    message: str
    thread_id: Optional[str] = None  # Optional thread for conversation context
    session_id: Optional[str] = None  # Optional session for anonymous users


@agent_api.api_operation(["GET", "POST", "OPTIONS"], "/stream", summary="Unified Agent Streaming Endpoint")
async def stream(request):
    """
    Unified streaming endpoint with thread and session support.

    Handles GET, POST, and OPTIONS requests:
    - OPTIONS /agent/stream           -> CORS preflight
    - GET  /agent/stream?message=...  -> Direct message streams (no persistence)
    - POST /agent/stream             -> User message streams via JSON body

    POST Body Options:
    {
      "message": "Hello, how does recursion work?",
      "thread_id": "optional-existing-thread-id",  // Continue existing thread
      "session_id": "optional-session-for-anonymous" // Anonymous user session
    }

    Conversation Management:
    - **Authenticated Users + thread_id**: Continue existing user-owned thread
    - **Authenticated Users + no thread_id**: Create new user thread
    - **Anonymous Users + session_id**: Create/use session-based anonymous thread
    - **Anonymous Users + no session_id**: Create anonymous thread with generated session
    - **No auth + no thread_id/session_id**: Simple one-off conversation (no persistence)

    Thread Migration:
    - Anonymous threads can be migrated to user ownership on login
    - Session threads become permanent when user authenticates

    Returns:
        SSEHttpResponse with Anthropic-compatible streaming events
    """

    # Handle CORS preflight
    if request.method == "OPTIONS":
        from django.http import HttpResponse
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        return response

    if request.method == "POST":
        # Handle POST request with JSON body
        try:
            data = json.loads(request.body)
            message = data.get("message", "")
            connect_only = data.get("connect_only", False)
            thread_id = data.get("thread_id")  # Optional thread context
            session_id = data.get("session_id")  # Optional session for anonymous users

            if not message and not connect_only:
                # Return error as SSE stream for consistency
                async def error_stream():
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Message required or connect_only=true'})}\n\n"
                response = SSEHttpResponse(error_stream())
                response["Access-Control-Allow-Origin"] = "*"
                return response

        except json.JSONDecodeError:
            # Return error as SSE stream for consistency
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Invalid JSON in request body'})}\n\n"
            response = SSEHttpResponse(error_stream())
            response["Access-Control-Allow-Origin"] = "*"
            return response

    else:  # GET request
        # Handle GET request with query parameters
        message = request.GET.get('message')
        user_state = request.GET.get('user_state', 'new_user')
        thread_id = request.GET.get('thread_id')

        logger.info(f"💬 [MESSAGE LIFECYCLE] Received message via GET: length={len(message or '')}, thread_id={thread_id}, user_id={user.id if user else None}, user_state={user_state}")

        if not message:
            # No hardcoded messages - return error if no message provided
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Message is required'})}\n\n"
            response = SSEHttpResponse(error_stream())
            response["Access-Control-Allow-Origin"] = "*"
            return response

    # Stream the agent response using AnthropicSSEGenerator
    try:
        # Handle thread/session context for conversation continuity
        thread_messages = None
        current_thread = None

        if request.method == "POST":
            # Try to authenticate user from JWT token
            user = None
            try:
                from yeshuman.api import get_user_from_token
                auth_header = request.headers.get('authorization', '')
                logger.info(f"🔐 Agent auth header: '{auth_header}'")
                user = await get_user_from_token(request)
                logger.info(f"🔐 Agent user extracted: {user}, type: {type(user)}, is_anon: {user.is_anonymous if user else 'N/A'}")
                if user and not user.is_anonymous:
                    logger.info(f"🔐 Authenticated user: {user.username} (id: {user.id})")
                else:
                    logger.info(f"🔐 Anonymous or no user: {user}")
            except Exception as e:
                logger.error(f"🔐 Agent auth error: {str(e)}")
                import traceback
                logger.error(f"🔐 Auth traceback: {traceback.format_exc()}")
                pass

            # Handle thread/session context
            if thread_id:
                logger.info(f"📂 [THREAD CONTEXT] Loading existing thread: thread_id={thread_id}")
                # User is referencing a specific thread
                try:
                    from apps.threads.services import get_thread, get_thread_messages_as_langchain
                    current_thread = await get_thread(thread_id)

                    # Check ownership
                    if current_thread and user and not user.is_anonymous:
                        if current_thread.user_id != str(user.id):
                            # User doesn't own this thread - create error
                            async def error_stream():
                                yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Access denied to this thread'})}\n\n"
                            sse_generator = AnthropicSSEGenerator()
                            response = SSEHttpResponse(sse_generator.generate_sse(error_stream()))
                            response["Access-Control-Allow-Origin"] = "*"
                            return response

                    if current_thread:
                        thread_messages = await get_thread_messages_as_langchain(thread_id)
                        # Add the new message to the thread
                        from apps.threads.services import create_human_message
                        await create_human_message(thread_id, message)

                except Exception as e:
                    logger.warning(f"Failed to load thread context: {str(e)}")
                    thread_messages = None

            elif session_id or (not user or user.is_anonymous):
                logger.info(f"📂 [THREAD CONTEXT] Using session-based thread: session_id={session_id}")
                # Anonymous user - create or get session-based thread
                try:
                    from apps.threads.services import get_session_threads, get_or_create_session_thread, get_thread_messages_as_langchain

                    # Get existing session threads
                    session_threads = await get_session_threads(session_id or "anonymous")

                    if session_threads:
                        # Use the most recent session thread
                        current_thread = session_threads[0]
                        thread_messages = await get_thread_messages_as_langchain(str(current_thread.id))
                        # Add message to existing thread
                        from apps.threads.services import create_human_message
                        await create_human_message(str(current_thread.id), message)
                    else:
                        # Create new session thread
                        current_thread = await get_or_create_session_thread(
                            session_id=session_id or "anonymous",
                            subject=f"Anonymous conversation - {message[:50]}..."
                        )
                        thread_messages = None  # No previous messages for new thread
                        # Add the initial message
                        from apps.threads.services import create_human_message
                        await create_human_message(str(current_thread.id), message)

                except Exception as e:
                    logger.warning(f"Failed to create session thread: {str(e)}")
                    thread_messages = None

        # Determine user focus for tool selection
        user_focus = None
        if user and not user.is_anonymous:
            logger.info(f"🎯 User authenticated: {user}, username: '{user.username}', id: {user.id}")
            from apps.accounts.utils import negotiate_user_focus
            user_focus, focus_error = negotiate_user_focus(request)
            if focus_error:
                logger.warning(f"Focus negotiation error for user {user.username}: {focus_error}")
                user_focus = 'candidate'  # Default fallback
            logger.info(f"🎯 Determined user focus: {user_focus}")
        else:
            logger.info(f"🎯 No authenticated user or anonymous user: {user}")

        # Handle connect_only mode for persistent real-time connections
        if connect_only:
            logger.info("🔄 Establishing persistent real-time connection (connect_only mode)")

            # Get authenticated user for persistent connection
            if not user or user.is_anonymous:
                async def error_stream():
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Authentication required for persistent connection'})}\n\n"
                response = SSEHttpResponse(error_stream())
                response["Access-Control-Allow-Origin"] = "*"
                return response

            # Create persistent connection for real-time updates
            async def persistent_stream_generator():
                import asyncio
                import time

                # Send connection confirmation
                yield {
                    "type": "connected",
                    "timestamp": int(time.time() * 1000),
                    "user_id": str(user.id),
                    "mode": "persistent"
                }

                # Keep connection alive with heartbeats
                counter = 0
                while True:
                    counter += 1

                    # Send heartbeat every 30 seconds
                    if counter % 30 == 0:
                        yield {
                            "type": "heartbeat",
                            "timestamp": int(time.time() * 1000)
                        }

                    await asyncio.sleep(1)

            sse_generator = AnthropicSSEGenerator()
            response = SSEHttpResponse(sse_generator.generate_sse(persistent_stream_generator()))
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Accept"
            return response

        # Create streaming generator with conversation context
        logger.info(f"🏁 [STREAM LIFECYCLE] Starting stream: thread_id={current_thread.id if current_thread else None}, user_id={user.id if user else None}")
        async def stream_generator():
            accumulated_response = []

            # Emit thread created event if this is a new thread
            if current_thread and hasattr(current_thread, '_was_created') and current_thread._was_created:
                logger.info(f"🔄 [DJANGO THREAD DELTA] Emitting thread_created: thread_id={current_thread.id}, subject='{current_thread.subject}', user_id={current_thread.user_id}, is_anonymous={current_thread.is_anonymous}")
                yield {
                    "type": "thread_created",
                    "thread_id": str(current_thread.id),
                    "subject": current_thread.subject,
                    "user_id": current_thread.user_id,
                    "is_anonymous": current_thread.is_anonymous,
                    "created_at": current_thread.created_at.isoformat()
                }

            # Emit human message saved event (message was saved during request processing)
            if current_thread:
                # Find the most recent human message for this thread
                try:
                    from apps.threads.models import HumanMessage
                    recent_human = await HumanMessage.objects.filter(thread=current_thread).order_by('-created_at').afirst()
                    if recent_human:
                        logger.info(f"🔄 [DJANGO THREAD DELTA] Emitting message_saved (human): thread_id={current_thread.id}, message_id={recent_human.id}, content_length={len(recent_human.text)}")
                        yield {
                            "type": "message_saved",
                            "thread_id": str(current_thread.id),
                            "message_id": str(recent_human.id),
                            "message_type": "human",
                            "content": recent_human.text[:200] + "..." if len(recent_human.text) > 200 else recent_human.text
                        }
                    else:
                        logger.warning(f"🔄 [DJANGO THREAD DELTA] No recent human message found for thread {current_thread.id}")
                except Exception as e:
                    logger.warning(f"Failed to emit human message delta: {str(e)}")

            async for chunk in astream_agent_tokens(message, thread_messages, user=user, focus=user_focus):
                # Accumulate message content for thread saving
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if isinstance(delta, dict) and "text" in delta:
                        content = delta["text"]
                        if content:
                            accumulated_response.append(content)
                elif chunk.get("type") == "message" and chunk.get("content"):
                    accumulated_response.append(chunk["content"])

                yield chunk

            # Save response to thread if we have one
            if current_thread and accumulated_response:
                try:
                    from apps.threads.services import create_assistant_message
                    full_response = "".join(accumulated_response)
                    assistant_message = await create_assistant_message(str(current_thread.id), full_response)

                    # Emit message saved event
                    logger.info(f"🔄 [DJANGO THREAD DELTA] Emitting message_saved (assistant): thread_id={current_thread.id}, message_id={assistant_message.id}, content_length={len(full_response)}")
                    yield {
                        "type": "message_saved",
                        "thread_id": str(current_thread.id),
                        "message_id": str(assistant_message.id),
                        "message_type": "assistant",
                        "content": full_response[:200] + "..." if len(full_response) > 200 else full_response
                    }

                    # Emit thread updated event
                    from apps.threads.models import Message
                    message_count = await Message.objects.filter(thread=current_thread).acount()
                    logger.info(f"🔄 [DJANGO THREAD DELTA] Emitting thread_updated: thread_id={current_thread.id}, message_count={message_count}")
                    yield {
                        "type": "thread_updated",
                        "thread_id": str(current_thread.id),
                        "message_count": message_count,
                        "updated_at": current_thread.updated_at.isoformat()
                    }

                except Exception as e:
                    logger.warning(f"Failed to save response to thread: {str(e)}")

        sse_generator = AnthropicSSEGenerator()
        response = SSEHttpResponse(sse_generator.generate_sse(stream_generator()))
        # Add CORS headers
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        return response

    except Exception as e:
        logger.error(f"Agent streaming error: {str(e)}")
        # Return error as SSE stream for consistency
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Agent execution encountered an error'})}\n\n"
        response = SSEHttpResponse(error_stream())
        response["Access-Control-Allow-Origin"] = "*"
        return response