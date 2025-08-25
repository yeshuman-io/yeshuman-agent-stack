import json
import logging

from ninja import NinjaAPI
from django.http import JsonResponse

from agent.agent import BookedAI
from agent.generators import SSEGenerator, SSEHttpResponse
from chats.services import get_all_chat_messages, get_or_create_chat

logger = logging.getLogger(__name__)

api = NinjaAPI()

@api.api_operation(["GET", "POST"], "/stream")
async def stream(request) -> SSEHttpResponse | JsonResponse:
    """
    Invoke the BookedAI agent in order to handle a human message or
    retrieve all messages for a given chat.
    
    Args:
        request: The HTTP request object

    Returns:
        A SSEHttpResponse or JsonResponse
    """
    bookedai = BookedAI()
    
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", "")
        chat_id = data.get("chat_id", None)  # Use None instead of empty string
        
        # Let handle_human_message create a new chat if chat_id is None
        message_obj = await bookedai.handle_human_message(message=message, chat_id=chat_id)
        
        # Use the new SSEHttpResponse which automatically sets the correct headers
        return SSEHttpResponse(
            bookedai.streaming_response(message_obj)
        )
    else:  # GET request
        chat_id = request.GET.get("chat_id")
        init_type = request.GET.get("init", "welcome")  # welcome, connect, or messages
        
        if init_type == "welcome":
            # Start a new chat with welcome message
            chat_obj, welcome_stream = await bookedai.handle_new_bookedai_chat()
            return SSEHttpResponse(welcome_stream)
            
        elif init_type == "connect":
            # Just establish SSE connection without creating chat or sending welcome
            async def empty_stream():
                # Send an initial connection success message
                yield {"type": "system", "content": "Connected to server"}
            return SSEHttpResponse(empty_stream())
            
        elif init_type == "messages" and chat_id:
            # Get existing chat messages
            messages_list, chat_obj = await get_all_chat_messages(chat_id)
            
            if chat_obj:
                return JsonResponse({
                    "chat_id": chat_obj.id,
                    "subject": chat_obj.subject or "",
                    "messages": messages_list,
                    "created_at": chat_obj.created_at.isoformat(),
                })
            else:
                return JsonResponse({
                    "error": "Chat not found"
                }, status=404)
        else:
            return JsonResponse({
                "error": "Invalid initialization type"
            }, status=400)
