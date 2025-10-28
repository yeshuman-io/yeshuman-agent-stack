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

# Import thread services
from apps.threads.services import handle_thread_title_generation, generate_thread_title_with_llm, update_thread_title


async def generate_and_update_thread_title(thread_id: str):
    """
    Async function to generate and update thread title.
    This runs in the background and doesn't emit deltas since the stream has already ended.
    """
    try:
        logger.info(f"🤖 [THREAD TITLE] Starting LLM title generation for thread {thread_id}")

        # Generate title
        title = await generate_thread_title_with_llm(thread_id)

        if title:
            # Update thread title
            success = await update_thread_title(thread_id, title)
            if success:
                logger.info(f"✅ [THREAD TITLE] Successfully generated and saved title: '{title}' for thread {thread_id}")
                # Note: UI will need to poll or use websockets to get title updates
                # since this happens after the stream ends
            else:
                logger.warning(f"❌ [THREAD TITLE] Failed to save generated title: '{title}' for thread {thread_id}")
        else:
            logger.warning(f"❌ [THREAD TITLE] LLM failed to generate valid title for thread {thread_id}")

    except Exception as e:
        logger.error(f"Error in async thread title generation: {e}")


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

    # Initialize variables for both request types
    connect_only = False
    session_id = None

    # Handle authentication for both GET and POST requests
    user = None
    try:
        from yeshuman.api import get_user_from_token
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            logger.info(f"🔐 Agent auth header: '{auth_header[:50]}...'")
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
        user = None  # No user authentication for GET requests

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
            # Handle thread/session context
            if thread_id:
                logger.info(f"📂 [THREAD CONTEXT] Loading existing thread: thread_id={thread_id}")
                # User is referencing a specific thread
                try:
                    from apps.threads.services import get_thread, get_thread_messages_as_langchain
                    current_thread = await get_thread(thread_id)

                    # Check ownership
                    if current_thread and user and not user.is_anonymous:
                        if str(current_thread.user_id) != str(user.id):
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
                        logger.info(f"💾 [MESSAGE SAVE] Saving human message to existing thread {thread_id}")
                        from apps.threads.services import create_human_message
                        human_message = await create_human_message(thread_id, message)
                        logger.info(f"💾 [MESSAGE SAVE] Successfully saved human message {human_message.id}")

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
                        logger.info(f"🆕 [THREAD CREATION] Creating new session thread for message: '{message[:50]}...'")
                        current_thread = await get_or_create_session_thread(
                            session_id=session_id or "anonymous",
                            subject=f"{message[:50]}..."
                        )
                        logger.info(f"🆕 [THREAD CREATION] Created session thread {current_thread.id}")
                        thread_messages = None  # No previous messages for new thread
                        # Add the initial message
                        logger.info(f"💾 [MESSAGE SAVE] Saving initial human message to new thread {current_thread.id}")
                        from apps.threads.services import create_human_message
                        human_message = await create_human_message(str(current_thread.id), message)
                        logger.info(f"💾 [MESSAGE SAVE] Successfully saved initial human message {human_message.id}")

                except Exception as e:
                    logger.warning(f"Failed to create session thread: {str(e)}")
                    thread_messages = None

            else:
                # Authenticated user without thread_id - create new user-owned thread
                logger.info(f"🆕 [THREAD CREATION] Creating new user thread for authenticated user: {user.username if user else 'unknown'}")
                try:
                    from apps.threads.services import get_or_create_thread
                    current_thread = await get_or_create_thread(
                        user_id=str(user.id) if user else None,
                        subject=f"{message[:50]}..."
                    )
                    logger.info(f"🆕 [THREAD CREATION] Created user thread {current_thread.id} for user {user.username if user else 'unknown'}")
                    thread_messages = None  # No previous messages for new thread
                    # Add the initial message
                    logger.info(f"💾 [MESSAGE SAVE] Saving initial human message to new user thread {current_thread.id}")
                    from apps.threads.services import create_human_message
                    human_message = await create_human_message(str(current_thread.id), message)
                    logger.info(f"💾 [MESSAGE SAVE] Successfully saved initial human message {human_message.id}")

                except Exception as e:
                    logger.warning(f"Failed to create user thread: {str(e)}")
                    thread_messages = None


        # Determine user focus for tool selection
        logger.info(f"🎯 Before focus negotiation: user={user}, type={type(user)}, is_anon={user.is_anonymous if user else 'N/A'}")
        user_focus = None
        if user and not user.is_anonymous:
            logger.info(f"🎯 User authenticated: {user}, username: '{user.username}', id: {user.id}")
            from apps.accounts.utils import negotiate_user_focus
            user_focus, focus_error = await negotiate_user_focus(request)
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
        logger.info(f"📨 [STREAM PARAMS] message='{message[:50]}...', thread_messages_count={len(thread_messages) if thread_messages else 0}, user={user.username if user else None}, focus={user_focus}")

        async def stream_generator():
            accumulated_response = []

            # Thread events are now emitted by graph nodes as UI deltas

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

            final_thread_id = str(current_thread.id) if current_thread else thread_id
            logger.info(f"🎬 [STREAM LIFECYCLE] Calling astream_agent_tokens with thread_id: {final_thread_id}")

            # Handle thread creation asynchronously (emit UI event)
            if final_thread_id and current_thread and hasattr(current_thread, '_was_created') and current_thread._was_created:
                async def _emit_thread_creation():
                    try:
                        from agent.mapper import create_thread_ui_event
                        # Create a mock writer that yields UI events as SSE
                        async def thread_writer(event):
                            ui_event = {
                                "type": "ui",
                                "entity": "thread",
                                "entity_id": final_thread_id,
                                "action": "created",
                                "subject": current_thread.subject or "New Conversation"
                            }
                            yield ui_event

                        # Emit thread creation event through the stream
                        async for event in thread_writer(None):
                            yield event
                            break  # Only emit once

                        logger.info(f"🆕 [THREAD CREATION] Emitted thread creation event for {final_thread_id}")
                    except Exception as e:
                        logger.warning(f"Failed to emit thread creation event: {e}")

                # Run thread creation emission
                async for event in _emit_thread_creation():
                    yield event

            logger.info(f"🎬 [STREAM LIFECYCLE] About to call astream_agent_tokens with user={user}, user.username={getattr(user, 'username', None)}, user.id={getattr(user, 'id', None)}, user.type={type(user)}")

            # Ensure conversation root trace exists and wrap turn in parent context
            from apps.threads.services import ensure_conversation_root_trace
            from agent.services.tracing import with_conversation_parent

            logger.info(f"🔗 [TRACE] Ensuring conversation root trace for thread {final_thread_id}")
            root_trace_id = await ensure_conversation_root_trace(final_thread_id, user)
            logger.info(f"🔗 [TRACE] Root trace ready: {root_trace_id}")
            turn_run_id = None

            logger.info(f"🚀 [STREAM] Starting async with conversation parent context")
            try:
                logger.info(f"🤖 [AGENT] About to call astream_agent_tokens")
                async with with_conversation_parent(root_trace_id):
                    logger.info(f"🔄 [STREAM] Entering async for loop for astream_agent_tokens")
                    async for chunk in astream_agent_tokens(message, None, user=user, focus=user_focus, thread_id=final_thread_id):
                        logger.info(f"📦 [CHUNK] Received chunk: {chunk.get('type', 'unknown')}")
                        # Capture turn run ID when emitted
                        if chunk.get("type") == "run_id" and chunk.get("runId"):
                            turn_run_id = chunk.get("runId")
                            logger.info(f"🔗 [TURN RUN ID] Captured turn run ID: {turn_run_id}")

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
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                raise
            finally:
                # ALWAYS save assistant message after streaming completes (success or failure)
                logger.info(f"🎯 [STREAM FINALLY] Executing finally block - current_thread={current_thread.id if current_thread else None}, turn_run_id={turn_run_id}, accumulated_response_len={len(accumulated_response) if accumulated_response else 0}")
                if current_thread:
                    try:
                        # Use accumulated content if available, otherwise fallback
                        if accumulated_response:
                            full_response = "".join(accumulated_response)
                        elif turn_run_id:
                            # If we have a run_id but no accumulated content, the response was generated
                            full_response = "[Assistant response was generated but content not captured]"
                            logger.warning(f"💾 [MESSAGE SAVE] No content accumulated but run_id exists, using fallback")
                        else:
                            # No response at all
                            full_response = "[Assistant response failed to generate]"
                            logger.warning(f"💾 [MESSAGE SAVE] No response content or run_id, using error fallback")

                        logger.info(f"💾 [MESSAGE SAVE] Saving assistant response to thread {current_thread.id}, response length: {len(full_response)}")

                        from apps.threads.services import create_assistant_message
                        assistant_message = await create_assistant_message(str(current_thread.id), full_response)

                        # Save turn run ID on the message for deep linking
                        if turn_run_id:
                            from asgiref.sync import sync_to_async
                            assistant_message.run_id = turn_run_id
                            await sync_to_async(assistant_message.save)()
                            logger.info(f"💾 [MESSAGE SAVE] Saved turn run ID {turn_run_id} on message {assistant_message.id}")

                        logger.info(f"💾 [MESSAGE SAVE] Successfully saved assistant message {assistant_message.id} (type={assistant_message.__class__.__name__})")

                        # Emit message saved event
                        logger.info(f"🔄 [DJANGO THREAD DELTA] Emitting message_saved (assistant): thread_id={current_thread.id}, message_id={assistant_message.id}, content_length={len(full_response)}")
                        yield {
                            "type": "message_saved",
                            "thread_id": str(current_thread.id),
                            "message_id": str(assistant_message.id),
                            "message_type": "assistant",
                            "content": full_response[:200] + "..." if len(full_response) > 200 else full_response
                        }

                    except Exception as e:
                        logger.error(f"❌ [MESSAGE SAVE] Failed to save assistant message: {str(e)}")
                        import traceback
                        logger.error(f"❌ [MESSAGE SAVE] Traceback: {traceback.format_exc()}")

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