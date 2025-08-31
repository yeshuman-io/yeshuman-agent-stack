"""
A2A Agent Cards - Standardized agent identity and capability description.
Based on emerging A2A specification standards.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from datetime import timezone as dt_timezone
import uuid


class AgentEndpoint(BaseModel):
    """Agent endpoint configuration."""
    url: str = Field(..., description="Endpoint URL")
    protocol: str = Field(..., description="Protocol type (mcp, a2a, rest, websocket)")
    version: Optional[str] = Field(None, description="Protocol version")
    authentication: Optional[List[str]] = Field(default_factory=list, description="Supported auth methods")


class AgentCapability(BaseModel):
    """Detailed capability description."""
    name: str = Field(..., description="Capability name")
    version: str = Field(default="1.0.0", description="Capability version")
    description: str = Field(..., description="Human-readable description")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for outputs")
    examples: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Usage examples")
    tags: Optional[List[str]] = Field(default_factory=list, description="Capability tags for discovery")


class AgentCard(BaseModel):
    """
    A2A Agent Card - Complete agent identity and capability specification.
    
    This follows emerging A2A standards for agent discovery and interoperability.
    """
    # Core Identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    version: str = Field(default="1.0.0", description="Agent version")
    description: str = Field(..., description="Agent description and purpose")
    
    # Capabilities
    capabilities: List[AgentCapability] = Field(default_factory=list, description="Detailed capability list")
    tags: List[str] = Field(default_factory=list, description="Discovery tags")
    
    # Endpoints
    endpoints: List[AgentEndpoint] = Field(default_factory=list, description="Available endpoints")
    
    # Operational Info
    status: str = Field(default="online", description="Current status (online, offline, busy, maintenance)")
    max_concurrent_tasks: Optional[int] = Field(default=10, description="Maximum concurrent task limit")
    response_time_sla: Optional[Dict[str, float]] = Field(None, description="Response time SLAs in seconds")
    
    # Metadata
    owner: Optional[str] = Field(None, description="Agent owner/organization")
    contact: Optional[str] = Field(None, description="Contact information")
    license: Optional[str] = Field(None, description="Usage license")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(dt_timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(dt_timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(dt_timezone.utc))
    
    # Advanced Features
    supports_streaming: bool = Field(default=False, description="Supports real-time streaming")
    supports_callbacks: bool = Field(default=False, description="Supports callback URLs")
    supports_async_tasks: bool = Field(default=False, description="Supports long-running async tasks")
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def add_capability(self, capability: AgentCapability):
        """Add a new capability to the agent."""
        self.capabilities.append(capability)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def matches_capability(self, required_capability: str) -> bool:
        """Check if agent has a specific capability."""
        return any(cap.name == required_capability for cap in self.capabilities)
    
    def matches_tags(self, required_tags: List[str]) -> bool:
        """Check if agent matches any of the required tags."""
        return bool(set(required_tags) & set(self.tags))


def create_yeshuman_agent_card() -> AgentCard:
    """Create the agent card for the Yes Human agent."""
    
    # Define capabilities
    capabilities = [
        AgentCapability(
            name="calculation",
            description="Perform mathematical calculations and computations",
            input_schema={"type": "object", "properties": {"expression": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
            tags=["math", "computation"]
        ),
        AgentCapability(
            name="conversation",
            description="Natural language conversation and question answering",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"response": {"type": "string"}}},
            tags=["nlp", "chat", "qa"]
        ),
        AgentCapability(
            name="weather_lookup",
            description="Get weather information for locations",
            input_schema={"type": "object", "properties": {"location": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"weather": {"type": "object"}}},
            tags=["weather", "lookup", "external-data"]
        ),
        AgentCapability(
            name="text_analysis",
            description="Analyze text for sentiment, word count, and summaries",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}, "analysis_type": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"analysis": {"type": "object"}}},
            tags=["nlp", "analysis", "sentiment"]
        ),
        AgentCapability(
            name="tool_coordination",
            description="Coordinate and orchestrate multiple tools and capabilities",
            input_schema={"type": "object", "properties": {"task": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "object"}}},
            tags=["orchestration", "coordination", "workflow"]
        )
    ]
    
    # Define endpoints
    endpoints = [
        AgentEndpoint(
            url="http://localhost:8000/mcp/",
            protocol="mcp",
            version="1.0",
            authentication=["none"]
        ),
        AgentEndpoint(
            url="http://localhost:8000/a2a/",
            protocol="a2a",
            version="1.0", 
            authentication=["api-key", "oauth2"]
        ),
        AgentEndpoint(
            url="http://localhost:8000/api/",
            protocol="rest",
            version="1.0",
            authentication=["none", "api-key"]
        )
    ]
    
    return AgentCard(
        name="Yes Human Agent",
        description="Multi-platform LangGraph ReAct agent with comprehensive tool integration and protocol support",
        capabilities=capabilities,
        endpoints=endpoints,
        tags=["langgraph", "react", "multi-platform", "calculation", "conversation", "weather", "text-analysis"],
        max_concurrent_tasks=10,
        response_time_sla={
            "simple_calculation": 1.0,
            "conversation": 5.0,
            "weather_lookup": 2.0,
            "text_analysis": 3.0
        },
        owner="Yes Human.io",
        contact="info@yeshuman.io",
        license="MIT",
        documentation_url="https://github.com/yeshuman-io/yeshuman-agent-stack",
        supports_streaming=True,
        supports_callbacks=True,
        supports_async_tasks=True
    )
