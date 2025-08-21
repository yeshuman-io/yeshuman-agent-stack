"""
A2A (Agent-to-Agent) API endpoints using Django Ninja.
"""
from ninja import NinjaAPI, Schema, Query
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import StreamingHttpResponse
from typing import List, Optional, Dict, Any
import json
import uuid

from .models import Agent, A2AMessage, Conversation, Task

# Create A2A API instance
a2a_api = NinjaAPI(
    title="YesHuman A2A Server",
    version="1.0.0",
    description="Agent-to-Agent communication server",
    urls_namespace="a2a"
)


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
            response_required=payload.response_required
        )
        
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
        return {"success": True, "status": message.status}
    except Exception as e:
        return {"error": str(e)}


# Task Management Endpoints

@a2a_api.post("/tasks/create", response=TaskResponse)
def create_task(request, payload: TaskRequest):
    """Create a new task."""
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
                
        except Agent.DoesNotExist:
            error_data = {'type': 'error', 'message': f'Agent {agent_name} not found'}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    
    return response


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
    
    response = StreamingHttpResponse(
        discovery_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    
    return response
