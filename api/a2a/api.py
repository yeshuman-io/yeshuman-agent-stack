"""
A2A (Agent-to-Agent) API endpoints using Django Ninja.
"""
from ninja import NinjaAPI, Schema, Query
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import StreamingHttpResponse
from utils.sse import SSEHttpResponse
from typing import List, Optional, Dict, Any
import json
import uuid

from .models import Agent, A2AMessage, Conversation, Task
from django.db import models
from .agent_cards import AgentCard, create_yeshuman_agent_card
from .async_tasks import async_task_manager, TaskStatus
from agent.graph import ainvoke_agent, astream_agent


# Create A2A API instance
a2a_api = NinjaAPI(
    title="YesHuman A2A Server",
    version="1.0.0",
    description="Agent-to-Agent communication server",
    urls_namespace="a2a"
)
# Minimal JSON-RPC 2.0 handler to support a2a-inspector chat
class JSONRPCRequest(Schema):
    jsonrpc: str
    method: str
    id: str
    params: Dict[str, Any]


@a2a_api.post("/", summary="A2A JSON-RPC endpoint (message/send)")
async def a2a_jsonrpc_handler(request, payload: JSONRPCRequest):
    # Check authentication
    from auth.backends import APIKeyUser
    
    # Check if user is authenticated via API key
    if not isinstance(request.user, APIKeyUser):
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Valid X-API-Key header required'
        }, status=401)
    
    try:
        if payload.jsonrpc != "2.0":
            return {"jsonrpc": "2.0", "id": payload.id, "error": {"code": -32600, "message": "Invalid Request"}}

        if payload.method == "message/send":
            message = payload.params.get("message", {})
            user_text = ""
            for part in message.get("parts", []):
                if isinstance(part, dict) and part.get("kind") == "text":
                    user_text = part.get("text", "")
                    break

            result = await ainvoke_agent(user_text)
            if not result.get("success"):
                return {"jsonrpc": "2.0", "id": payload.id, "error": {"code": -32000, "message": result.get("error", "Agent error")}}

            response_message = {
                "messageId": str(uuid.uuid4()),
                "role": "agent",
                "parts": [{"kind": "text", "text": result["response"]}],
            }
            return {"jsonrpc": "2.0", "id": payload.id, "result": response_message}

        elif payload.method == "message/stream":
            message = payload.params.get("message", {})
            user_text = ""
            for part in message.get("parts", []):
                if isinstance(part, dict) and part.get("kind") == "text":
                    user_text = part.get("text", "")
                    break

            def event_stream():
                try:
                    # First, send initial Task object
                    task_id = str(uuid.uuid4())
                    context_id = str(uuid.uuid4())
                    
                    initial_task = {
                        "kind": "task",
                        "id": task_id,
                        "contextId": context_id,
                        "status": {
                            "state": "working",
                            "timestamp": timezone.now().isoformat()
                        },
                        "history": [
                            {
                                "messageId": message.get("messageId", str(uuid.uuid4())),
                                "role": "user", 
                                "parts": [{"kind": "text", "text": user_text}]
                            }
                        ]
                    }
                    obj = {"jsonrpc": "2.0", "id": payload.id, "result": initial_task}
                    yield f"data: {json.dumps(obj)}\n\n"
                    
                    # Stream agent response token by token
                    import asyncio
                    
                    async def async_streaming():
                        try:
                            async for token in astream_agent(user_text):
                                response_message = {
                                    "kind": "message",
                                    "messageId": str(uuid.uuid4()),
                                    "role": "agent",
                                    "parts": [{"kind": "text", "text": token}],
                                    "taskId": task_id
                                }
                                obj = {"jsonrpc": "2.0", "id": payload.id, "result": response_message}
                                yield f"data: {json.dumps(obj)}\n\n"
                        except Exception as stream_e:
                            error_obj = {"jsonrpc": "2.0", "id": payload.id, "error": {"code": -32000, "message": f"Streaming error: {str(stream_e)}"}}
                            yield f"data: {json.dumps(error_obj)}\n\n"
                    
                    # Run async streaming in the sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        async_gen = async_streaming()
                        while True:
                            try:
                                chunk = loop.run_until_complete(async_gen.__anext__())
                                yield chunk
                            except StopAsyncIteration:
                                break
                    finally:
                        loop.close()
                    
                    # Send final status update
                    status_update = {
                        "kind": "status-update",
                        "taskId": task_id,
                        "contextId": context_id,
                        "final": True,
                        "status": {
                            "state": "completed",
                            "timestamp": timezone.now().isoformat()
                        }
                    }
                    obj = {"jsonrpc": "2.0", "id": payload.id, "result": status_update}
                    yield f"data: {json.dumps(obj)}\n\n"
                    
                except Exception as inner_e:
                    error_obj = {"jsonrpc": "2.0", "id": payload.id, "error": {"code": -32603, "message": f"Internal error: {str(inner_e)}"}}
                    yield f"data: {json.dumps(error_obj)}\n\n"

            return SSEHttpResponse(event_stream())

        return {"jsonrpc": "2.0", "id": payload.id, "error": {"code": -32601, "message": "Method not found"}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": payload.id, "error": {"code": -32603, "message": f"Internal error: {str(e)}"}}


@a2a_api.post("/stream", summary="A2A JSON-RPC streaming endpoint (message/stream)")
async def a2a_jsonrpc_stream_handler(request):
    # Check authentication
    from auth.backends import APIKeyUser
    
    # Check if user is authenticated via API key
    if not isinstance(request.user, APIKeyUser):
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Valid X-API-Key header required'
        }, status=401)
    
    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
        jsonrpc = body.get("jsonrpc")
        method = body.get("method")
        request_id = body.get("id", str(uuid.uuid4()))
        params = body.get("params", {})

        if jsonrpc != "2.0" or method != "message/stream":
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}

        message = params.get("message", {})
        user_text = ""
        for part in message.get("parts", []):
            if isinstance(part, dict) and part.get("type") in ["text", "text/plain"]:
                user_text = part.get("text") or part.get("data") or ""
                break

        async def event_stream():
            try:
                result = await ainvoke_agent(user_text)
                if not result.get("success"):
                    error_obj = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": result.get("error", "Agent error")}}
                    yield f"data: {json.dumps(error_obj)}\n\n"
                    return

                full_text = str(result["response"]) if result.get("response") is not None else ""

                # Stream in simple chunks to demonstrate streaming compatibility
                chunks = [full_text[i:i+200] for i in range(0, len(full_text), 200)] or [""]
                for idx, chunk in enumerate(chunks):
                    response_message = {
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "parts": [{"type": "text/plain", "data": chunk}],
                        "is_final": idx == len(chunks) - 1,
                    }
                    obj = {"jsonrpc": "2.0", "id": request_id, "result": response_message}
                    yield f"data: {json.dumps(obj)}\n\n"
            except Exception as inner_e:
                error_obj = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": f"Internal error: {str(inner_e)}"}}
                yield f"data: {json.dumps(error_obj)}\n\n"

        return SSEHttpResponse(event_stream())
    except Exception as e:
        return {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "error": {"code": -32603, "message": f"Internal error: {str(e)}"}}


# Schemas
class AgentRegisterRequest(Schema):
    name: str
    endpoint_url: Optional[str] = None
    capabilities: List[str] = []
    metadata: Dict[str, Any] = {}


class AgentResponse(Schema):
    id: str
    name: str
    endpoint_url: Optional[str]
    capabilities: List[str]
    status: str
    last_seen: str
    metadata: Dict[str, Any]


class MessageRequest(Schema):
    to_agent: str  # agent name or ID
    message_type: str = "request"
    subject: Optional[str] = ""
    payload: Dict[str, Any]
    priority: int = 3
    response_required: bool = False
    conversation_id: Optional[str] = None
    callback_url: Optional[str] = None


class MessageResponse(Schema):
    id: str
    from_agent: str
    to_agent: Optional[str]
    message_type: str
    subject: str
    payload: Dict[str, Any]
    status: str
    priority: int
    created_at: str
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    conversation_id: Optional[str]


class TaskRequest(Schema):
    assigned_to: Optional[str] = None  # agent name
    title: str
    description: str = ""
    task_type: str = "general"
    parameters: Dict[str, Any] = {}
    due_date: Optional[str] = None


class TaskResponse(Schema):
    id: str
    created_by: str
    assigned_to: Optional[str]
    title: str
    description: str
    task_type: str
    status: str
    progress: int
    result: Optional[Dict[str, Any]]
    created_at: str


# Agent Management Endpoints

@a2a_api.post("/agents/register", response=AgentResponse)
def register_agent(request, payload: AgentRegisterRequest):
    """Register a new agent or update existing one."""
    # Check authentication
    from auth.backends import APIKeyUser
    
    # Check if user is authenticated via API key
    if not isinstance(request.user, APIKeyUser):
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Valid X-API-Key header required'
        }, status=401)
    
    try:
        agent, created = Agent.objects.get_or_create(
            name=payload.name,
            defaults={
                'endpoint_url': payload.endpoint_url,
                'capabilities': payload.capabilities,
                'metadata': payload.metadata,
                'status': 'online'
            }
        )
        
        if not created:
            # Update existing agent
            agent.endpoint_url = payload.endpoint_url
            agent.capabilities = payload.capabilities
            agent.metadata = payload.metadata
            agent.status = 'online'
            agent.update_heartbeat()
            agent.save()
        
        return AgentResponse(
            id=str(agent.id),
            name=agent.name,
            endpoint_url=agent.endpoint_url,
            capabilities=agent.capabilities,
            status=agent.status,
            last_seen=agent.last_seen.isoformat(),
            metadata=agent.metadata
        )
    except Exception as e:
        return {"error": str(e)}


@a2a_api.delete("/agents/{agent_name}")
def unregister_agent(request, agent_name: str):
    """Unregister an agent."""
    try:
        agent = get_object_or_404(Agent, name=agent_name)
        agent.status = 'offline'
        agent.save()
        return {"success": True, "message": f"Agent {agent_name} unregistered"}
    except Exception as e:
        return {"error": str(e)}


@a2a_api.get("/discover", response=List[AgentResponse])
def discover_agents(request, capabilities: str = Query(None), status: str = Query("online")):
    """Discover available agents."""
    try:
        agents = Agent.objects.filter(status=status)
        
        if capabilities:
            cap_list = [cap.strip() for cap in capabilities.split(',')]
            # Filter agents that have ANY of the requested capabilities
            # Simple approach that works with all databases
            filtered_agents = []
            for agent in agents:
                if any(cap in agent.capabilities for cap in cap_list):
                    filtered_agents.append(agent)
            agents = filtered_agents
        
        return [
            AgentResponse(
                id=str(agent.id),
                name=agent.name,
                endpoint_url=agent.endpoint_url,
                capabilities=agent.capabilities,
                status=agent.status,
                last_seen=agent.last_seen.isoformat(),
                metadata=agent.metadata
            )
            for agent in agents
        ]
    except Exception as e:
        return {"error": str(e)}


@a2a_api.post("/agents/{agent_name}/heartbeat")
def agent_heartbeat(request, agent_name: str):
    """Update agent heartbeat."""
    try:
        agent = get_object_or_404(Agent, name=agent_name)
        agent.update_heartbeat()
        return {"success": True, "last_seen": agent.last_seen.isoformat()}
    except Exception as e:
        return {"error": str(e)}


# Message Endpoints

@a2a_api.post("/messages/send", response=MessageResponse)
def send_message(request, payload: MessageRequest):
    """Send a message to another agent."""
    try:
        # Get the sending agent from request headers or authentication
        from_agent_name = request.headers.get('X-Agent-Name', 'unknown')
        from_agent = get_object_or_404(Agent, name=from_agent_name)
        
        # Get target agent
        to_agent = None
        if payload.to_agent:
            to_agent = get_object_or_404(Agent, name=payload.to_agent)
        
        # Get conversation if provided
        conversation = None
        if payload.conversation_id:
            conversation = get_object_or_404(Conversation, id=payload.conversation_id)
        
        # Create message
        message = A2AMessage.objects.create(
            from_agent=from_agent,
            to_agent=to_agent,
            conversation=conversation,
            message_type=payload.message_type,
            subject=payload.subject,
            payload=payload.payload,
            priority=payload.priority,
            response_required=payload.response_required,
            callback_url=payload.callback_url
        )
        
        # Trigger callback (sent) in background if provided
        if message.callback_url:
            import threading
            threading.Thread(target=_send_message_callback_safe, args=(str(message.id), 'sent')).start()

        return MessageResponse(
            id=str(message.id),
            from_agent=message.from_agent.name,
            to_agent=message.to_agent.name if message.to_agent else None,
            message_type=message.message_type,
            subject=message.subject,
            payload=message.payload,
            status=message.status,
            priority=message.priority,
            created_at=message.created_at.isoformat(),
            delivered_at=message.delivered_at.isoformat() if message.delivered_at else None,
            read_at=message.read_at.isoformat() if message.read_at else None,
            conversation_id=str(message.conversation.id) if message.conversation else None
        )
    except Exception as e:
        return {"error": str(e)}


@a2a_api.get("/messages/{agent_name}", response=List[MessageResponse])
def get_messages(request, agent_name: str, status: str = "pending", limit: int = 50):
    """Get pending messages for an agent."""
    try:
        agent = get_object_or_404(Agent, name=agent_name)
        messages = A2AMessage.objects.filter(
            to_agent=agent,
            status=status
        ).order_by('-created_at')[:limit]
        
        return [
            MessageResponse(
                id=str(msg.id),
                from_agent=msg.from_agent.name,
                to_agent=msg.to_agent.name if msg.to_agent else None,
                message_type=msg.message_type,
                subject=msg.subject,
                payload=msg.payload,
                status=msg.status,
                priority=msg.priority,
                created_at=msg.created_at.isoformat(),
                conversation_id=str(msg.conversation.id) if msg.conversation else None
            )
            for msg in messages
        ]
    except Exception as e:
        return {"error": str(e)}


@a2a_api.post("/messages/{message_id}/mark_read")
def mark_message_read(request, message_id: str):
    """Mark a message as read."""
    try:
        message = get_object_or_404(A2AMessage, id=message_id)
        message.mark_read()
        # Callback for read
        if message.callback_url:
            import threading
            threading.Thread(target=_send_message_callback_safe, args=(str(message.id), 'read')).start()
        return {"success": True, "status": message.status}
    except Exception as e:
        return {"error": str(e)}


# --- Message Callback Utilities ---
def _send_message_callback_safe(message_id: str, event: str):
    """Send callback notification safely, updating delivery attempts and errors."""
    try:
        from .models import A2AMessage
        import requests
        from django.db import transaction
        msg = A2AMessage.objects.get(id=message_id)
        if not msg.callback_url:
            return
        payload = {
            "message_id": str(msg.id),
            "event": event,
            "status": msg.status,
            "from_agent": msg.from_agent.name,
            "to_agent": msg.to_agent.name if msg.to_agent else None,
            "message_type": msg.message_type,
            "subject": msg.subject,
            "created_at": msg.created_at.isoformat(),
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
        }
        try:
            requests.post(msg.callback_url, json=payload, timeout=5)
            with transaction.atomic():
                A2AMessage.objects.filter(id=message_id).update(delivery_attempts=models.F('delivery_attempts') + 1, last_error="")
        except Exception as cb_err:
            with transaction.atomic():
                A2AMessage.objects.filter(id=message_id).update(delivery_attempts=models.F('delivery_attempts') + 1, last_error=str(cb_err))
    except Exception:
        # Fail silently; we do not want callbacks to crash the request
        pass


# Task Management Endpoints

@a2a_api.post("/tasks/create", response=TaskResponse)
def create_task(request, payload: TaskRequest):
    """Create a new task."""
    # Check authentication
    from auth.backends import APIKeyUser
    
    # Check if user is authenticated via API key
    if not isinstance(request.user, APIKeyUser):
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Valid X-API-Key header required'
        }, status=401)
    
    try:
        # Get the creating agent
        creator_name = request.headers.get('X-Agent-Name', 'unknown')
        creator = get_object_or_404(Agent, name=creator_name)
        
        # Get assigned agent if specified
        assigned_agent = None
        if payload.assigned_to:
            assigned_agent = get_object_or_404(Agent, name=payload.assigned_to)
        
        # Parse due date if provided
        due_date = None
        if payload.due_date:
            due_date = timezone.datetime.fromisoformat(payload.due_date)
        
        task = Task.objects.create(
            created_by=creator,
            assigned_to=assigned_agent,
            title=payload.title,
            description=payload.description,
            task_type=payload.task_type,
            parameters=payload.parameters,
            due_date=due_date
        )
        
        if assigned_agent:
            task.assign_to(assigned_agent)
        
        return TaskResponse(
            id=str(task.id),
            created_by=task.created_by.name,
            assigned_to=task.assigned_to.name if task.assigned_to else None,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            status=task.status,
            progress=task.progress,
            result=task.result,
            created_at=task.created_at.isoformat()
        )
    except Exception as e:
        return {"error": str(e)}


@a2a_api.get("/tasks/{agent_name}", response=List[TaskResponse])
def get_agent_tasks(request, agent_name: str, status: str = "assigned"):
    """Get tasks for an agent."""
    try:
        agent = get_object_or_404(Agent, name=agent_name)
        tasks = Task.objects.filter(assigned_to=agent, status=status)
        
        return [
            TaskResponse(
                id=str(task.id),
                created_by=task.created_by.name,
                assigned_to=task.assigned_to.name if task.assigned_to else None,
                title=task.title,
                description=task.description,
                task_type=task.task_type,
                status=task.status,
                progress=task.progress,
                result=task.result,
                created_at=task.created_at.isoformat()
            )
            for task in tasks
        ]
    except Exception as e:
        return {"error": str(e)}


# SSE Endpoints for Real-time Communication

@a2a_api.get("/stream/{agent_name}")
def agent_message_stream(request, agent_name: str):
    """SSE stream for real-time messages to an agent."""
    
    def event_stream():
        """Generate SSE events for incoming messages."""
        try:
            agent = Agent.objects.get(name=agent_name)
            
            # Send connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'agent': agent_name})}\n\n"
            
            # Get pending messages
            messages = A2AMessage.objects.filter(
                to_agent=agent,
                status='pending'
            ).order_by('created_at')
            
            for message in messages:
                message_data = {
                    'type': 'message',
                    'id': str(message.id),
                    'from_agent': message.from_agent.name,
                    'message_type': message.message_type,
                    'subject': message.subject,
                    'payload': message.payload,
                    'priority': message.priority,
                    'created_at': message.created_at.isoformat()
                }
                yield f"data: {json.dumps(message_data)}\n\n"
                
                # Mark as delivered
                message.mark_delivered()
                # Callback for delivered
                if message.callback_url:
                    import threading
                    threading.Thread(target=_send_message_callback_safe, args=(str(message.id), 'delivered')).start()
                
        except Agent.DoesNotExist:
            error_data = {'type': 'error', 'message': f'Agent {agent_name} not found'}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return SSEHttpResponse(event_stream())


@a2a_api.get("/stream/discovery")
def agent_discovery_stream(request):
    """SSE stream for agent presence updates."""
    
    def discovery_stream():
        """Generate SSE events for agent presence."""
        agents = Agent.objects.filter(status='online')
        
        agents_data = {
            'type': 'agents_online',
            'agents': [
                {
                    'name': agent.name,
                    'capabilities': agent.capabilities,
                    'last_seen': agent.last_seen.isoformat()
                }
                for agent in agents
            ]
        }
        yield f"data: {json.dumps(agents_data)}\n\n"
    
    return SSEHttpResponse(discovery_stream())


# Agent Cards - A2A Specification Compliance
class AgentCardResponse(Schema):
    """Agent card response schema."""
    agent_card: Dict[str, Any]
    

@a2a_api.get("/agent-card", response=AgentCardResponse, summary="Get YesHuman Agent Card")
def get_agent_card(request):
    """
    Get the standardized A2A Agent Card for the YesHuman agent.
    
    Agent Cards provide a comprehensive description of agent capabilities,
    endpoints, and metadata following A2A specification standards.
    """
    try:
        agent_card = create_yeshuman_agent_card()
        return {"agent_card": agent_card.model_dump()}
    except Exception as e:
        return a2a_api.create_response(
            request,
            {"error": f"Failed to generate agent card: {str(e)}"},
            status=500
        )


@a2a_api.get("/agent-card/a2a", summary="Get A2A-spec Agent Card (for inspector)")
def get_agent_card_a2a(request):
    """Return an A2A-spec AgentCard shape expected by a2a-inspector."""
    try:
        card = {
            "name": "YesHuman Agent",
            "version": "1.0.0",
            "description": "Multi-platform LangGraph ReAct agent with comprehensive tool integration and protocol support",
            "url": "http://localhost:8000/a2a/",
            "preferredTransport": "JSONRPC",
            "protocolVersion": "0.3.0",
            "capabilities": {"streaming": True},
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "skills": [
                {
                    "id": "conversation",
                    "name": "Conversation",
                    "description": "Natural language conversation and question answering",
                    "tags": ["nlp", "chat", "qa"],
                    "inputModes": ["text/plain"],
                    "outputModes": ["text/plain"],
                },
                {
                    "id": "calculation",
                    "name": "Calculation",
                    "description": "Perform mathematical calculations and computations",
                    "tags": ["math", "computation"],
                    "inputModes": ["text/plain"],
                    "outputModes": ["text/plain"],
                },
                {
                    "id": "weather_lookup",
                    "name": "Weather Lookup",
                    "description": "Get weather information for locations",
                    "tags": ["weather", "lookup", "external-data"],
                    "inputModes": ["text/plain"],
                    "outputModes": ["text/plain"],
                },
                {
                    "id": "text_analysis",
                    "name": "Text Analysis",
                    "description": "Analyze text for sentiment, word count, and summaries",
                    "tags": ["nlp", "analysis", "sentiment"],
                    "inputModes": ["text/plain"],
                    "outputModes": ["text/plain"],
                },
            ],
            "documentationUrl": "https://github.com/yeshuman-io/yeshuman-agent-stack",
            "provider": {"organization": "YesHuman.io", "url": "https://yeshuman.io"},
        }
        return card
    except Exception as e:
        return a2a_api.create_response(request, {"error": f"Failed to generate A2A card: {str(e)}"}, status=500)


@a2a_api.get("/agent-card/{agent_name}", response=AgentCardResponse, summary="Get Agent Card by Name")
def get_agent_card_by_name(request, agent_name: str):
    """
    Get agent card for a specific registered agent.
    
    For now, this only supports the YesHuman agent, but could be extended
    to support multiple agents in a multi-agent system.
    """
    try:
        if agent_name.lower() in ["yeshuman", "yeshuman-agent"]:
            agent_card = create_yeshuman_agent_card()
            return {"agent_card": agent_card.model_dump()}
        else:
            return a2a_api.create_response(
                request,
                {"error": f"Agent '{agent_name}' not found"},
                status=404
            )
    except Exception as e:
        return a2a_api.create_response(
            request,
            {"error": f"Failed to get agent card: {str(e)}"},
            status=500
        )


class CapabilityMatchRequest(Schema):
    """Request schema for capability matching."""
    required_capabilities: List[str] = []
    required_tags: List[str] = []
    

class CapabilityMatchResponse(Schema):
    """Response schema for capability matching."""
    matches: bool
    agent_card: Optional[Dict[str, Any]] = None
    matching_capabilities: List[str] = []
    matching_tags: List[str] = []


@a2a_api.post("/capability-match", response=CapabilityMatchResponse, summary="Match Agent Capabilities")
def match_capabilities(request, payload: CapabilityMatchRequest):
    """
    Check if the YesHuman agent matches specific capability requirements.
    
    This is useful for agent discovery and task routing in multi-agent systems.
    """
    try:
        agent_card = create_yeshuman_agent_card()
        
        # Check capability matches
        matching_capabilities = []
        for req_cap in payload.required_capabilities:
            if agent_card.matches_capability(req_cap):
                matching_capabilities.append(req_cap)
        
        # Check tag matches
        matching_tags = []
        if payload.required_tags:
            matching_tags = list(set(payload.required_tags) & set(agent_card.tags))
        
        # Determine if it's a match
        caps_match = len(matching_capabilities) == len(payload.required_capabilities) if payload.required_capabilities else True
        tags_match = len(matching_tags) > 0 if payload.required_tags else True
        
        matches = caps_match and tags_match
        
        return {
            "matches": matches,
            "agent_card": agent_card.model_dump() if matches else None,
            "matching_capabilities": matching_capabilities,
            "matching_tags": matching_tags
        }
        
    except Exception as e:
        return a2a_api.create_response(
            request,
            {"error": f"Capability matching failed: {str(e)}"},
            status=500
        )


# Async Task Management - Long-running Operations
class AsyncTaskRequest(Schema):
    """Request schema for creating async tasks."""
    task_type: str
    params: Dict[str, Any] = {}
    callback_url: Optional[str] = None


class AsyncTaskResponse(Schema):
    """Response schema for async task operations."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(Schema):
    """Response schema for task status queries."""
    task_id: str
    status: str
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@a2a_api.post("/async-tasks", response=AsyncTaskResponse, summary="Create Async Task")
def create_async_task(request, payload: AsyncTaskRequest):
    """
    Create a long-running async task that can exceed normal HTTP timeouts.
    
    Supports task types:
    - long_calculation: Extended mathematical computations
    - data_analysis: Large dataset processing
    - web_research: Multi-source information gathering
    - file_processing: Large file analysis
    """
    try:
        task_id = async_task_manager.create_task(
            task_type=payload.task_type,
            params=payload.params,
            callback_url=payload.callback_url
        )
        
        return {
            "task_id": task_id,
            "status": "created",
            "message": f"Async task '{payload.task_type}' created successfully"
        }
        
    except ValueError as e:
        return a2a_api.create_response(
            request,
            {"error": str(e)},
            status=400
        )
    except Exception as e:
        return a2a_api.create_response(
            request,
            {"error": f"Failed to create async task: {str(e)}"},
            status=500
        )


@a2a_api.get("/async-tasks/{task_id}", response=TaskStatusResponse, summary="Get Task Status")
def get_task_status(request, task_id: str):
    """
    Get the current status and progress of an async task.
    
    Returns real-time progress updates and results when completed.
    """
    try:
        task_result = async_task_manager.get_task_status(task_id)
        
        if not task_result:
            return a2a_api.create_response(
                request,
                {"error": f"Task '{task_id}' not found"},
                status=404
            )
        
        return {
            "task_id": task_result.task_id,
            "status": task_result.status.value,
            "progress": task_result.progress,
            "result": task_result.result,
            "error": task_result.error,
            "started_at": task_result.started_at.isoformat() if task_result.started_at else None,
            "completed_at": task_result.completed_at.isoformat() if task_result.completed_at else None
        }
        
    except Exception as e:
        return a2a_api.create_response(
            request,
            {"error": f"Failed to get task status: {str(e)}"},
            status=500
        )


@a2a_api.delete("/async-tasks/{task_id}", response=AsyncTaskResponse, summary="Cancel Task")
def cancel_task(request, task_id: str):
    """
    Cancel a running async task.
    
    Tasks that are already completed cannot be cancelled.
    """
    try:
        success = async_task_manager.cancel_task(task_id)
        
        if success:
            return {
                "task_id": task_id,
                "status": "cancelled",
                "message": "Task cancelled successfully"
            }
        else:
            return a2a_api.create_response(
                request,
                {"error": f"Task '{task_id}' not found or cannot be cancelled"},
                status=404
            )
            
    except Exception as e:
        return a2a_api.create_response(
            request,
            {"error": f"Failed to cancel task: {str(e)}"},
            status=500
        )


class TaskTypesResponse(Schema):
    """Response schema for available task types."""
    task_types: List[Dict[str, str]]


@a2a_api.get("/task-types", response=TaskTypesResponse, summary="List Available Task Types")
def list_task_types(request):
    """
    List all available async task types and their descriptions.
    """
    task_types = [
        {
            "type": "long_calculation",
            "description": "Extended mathematical computations that may take several minutes",
            "example_params": '{"expression": "2+2", "iterations": 1000}'
        },
        {
            "type": "data_analysis", 
            "description": "Large dataset processing and statistical analysis",
            "example_params": '{"data_size": 10000, "analysis_type": "statistical"}'
        },
        {
            "type": "web_research",
            "description": "Multi-source information gathering and research",
            "example_params": '{"query": "artificial intelligence", "num_sources": 10}'
        },
        {
            "type": "file_processing",
            "description": "Large file analysis and content extraction",
            "example_params": '{"file_type": "text", "file_size_mb": 100}'
        }
    ]
    
    return {"task_types": task_types}
