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
            thread_id = data.get("thread_id")  # Optional thread context
            session_id = data.get("session_id")  # Optional session for anonymous users

            if not message:
                # Return error as SSE stream for consistency
                async def error_stream():
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'content': 'Message is required in POST body'})}\n\n"
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
                user = await get_user_from_token(request)
            except:
                pass

            # Handle thread/session context
            if thread_id:
                # User is referencing a specific thread
                try:
                    from threads.services import get_thread, get_thread_messages_as_langchain
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
                        from threads.services import create_human_message
                        await create_human_message(thread_id, message)

                except Exception as e:
                    logger.warning(f"Failed to load thread context: {str(e)}")
                    thread_messages = None

            elif session_id or (not user or user.is_anonymous):
                # Anonymous user - create or get session-based thread
                try:
                    from threads.services import get_session_threads, get_or_create_session_thread, get_thread_messages_as_langchain

                    # Get existing session threads
                    session_threads = await get_session_threads(session_id or "anonymous")

                    if session_threads:
                        # Use the most recent session thread
                        current_thread = session_threads[0]
                        thread_messages = await get_thread_messages_as_langchain(str(current_thread.id))
                        # Add message to existing thread
                        from threads.services import create_human_message
                        await create_human_message(str(current_thread.id), message)
                    else:
                        # Create new session thread
                        current_thread = await get_or_create_session_thread(
                            session_id=session_id or "anonymous",
                            subject=f"Anonymous conversation - {message[:50]}..."
                        )
                        thread_messages = None  # No previous messages for new thread
                        # Add the initial message
                        from threads.services import create_human_message
                        await create_human_message(str(current_thread.id), message)

                except Exception as e:
                    logger.warning(f"Failed to create session thread: {str(e)}")
                    thread_messages = None

        # Create streaming generator with conversation context
        async def stream_generator():
            accumulated_response = []

            async for chunk in astream_agent_tokens(message, thread_messages):
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
                    from threads.services import create_assistant_message
                    full_response = "".join(accumulated_response)
                    await create_assistant_message(str(current_thread.id), full_response)
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