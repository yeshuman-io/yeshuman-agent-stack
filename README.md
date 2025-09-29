# Yes Human Agent Stack

## Primary Goal

Build applications for clients (and myself) using a set of opinions and rules embodied in code that allows co-authoring production-ready MVPs or PoCs with mostly AI-assisted coding pipelines/sessions.

## Core Components

**Django Foundation**
- Django + Django Ninja API backend
- Django-first auth solution (replaceable by auth providers later)
- Serves API endpoints to client applications
- MCP server implementation
- A2A (Agent-to-Agent) server implementation

**LangGraph Integration**
- Begin with LangGraph pre-builts before custom node design
- LangGraph agent chat for immediate capability exploration
- Agent-centric workflows and tooling

**Dependency Philosophy**
- Minimal dependencies chosen carefully
- Examine candidates thoroughly before adoption
- Borrow proven patterns from existing projects

## Success Criteria

1. **Production Ready**: MVPs that can ship to clients
2. **AI-Assisted Development**: Optimized for AI coding sessions
3. **Immediate Agent Exploration**: Working chat interface from day one
4. **Extensible Architecture**: Clean foundation for custom development
5. **Code Reuse**: Best patterns from existing projects consolidated

## Technical Architecture

- **Backend**: Django + Django Ninja + LangGraph
- **Agent Framework**: LangGraph (pre-builts → custom nodes)
- **Protocols**: MCP server, A2A communication
- **Auth**: Django-first (Auth0/Clerk migration path)
- **API**: RESTful endpoints via Django Ninja
- **Chat**: LangGraph agent chat interface
- **Package Management**: UV exclusively for Django/Python
- **Database**: PostgreSQL + pgvector by default
- **Testing**: pytest
- **Development Data**: Synthetic data generation for early development

## Development Philosophy

**Opinionated Structure**: Clear conventions over configuration
**Simplicity First**: Start minimal, add complexity only when needed  
**Agent-Centric**: Built around LangGraph agent workflows
**Client-Ready**: Every component should support production deployment
**AI-Assisted Workflows**: Cursor rules and workflows provide agent visibility to terminals for test output and logs
**UV-First**: Exclusive use of UV for Python package management
**Test-Driven**: pytest integration from day one
**Synthetic Data**: Generate realistic test data for rapid development iteration
**Single Runtime**: Django is the ONLY runtime - MCP and A2A must be served by Django and Ninja, no standalone servers

## Current Status

### ✅ Completed
- **Python Environment**: Python 3.13.2 (latest available via UV)
- **Django Project**: Django 5.2.5 initialized and tested
- **Package Management**: UV virtual environment configured
- **Project Structure**: Complete Django project with organized API modules
- **MCP Server**: Full Model Context Protocol implementation with JSON-RPC 2.0
- **MCP Client**: Stdio-based MCP client for integration with MCP-compatible tools
- **A2A Server**: Complete Agent-to-Agent communication protocol with REST API
- **Tool System**: LangChain BaseTool integration (Calculator, Echo, Weather, Text Analysis, Agent Chat, Agent Capabilities)
- **Agent Integration**: LangGraph ReAct agent with automatic tool discovery
- **Testing Suite**: Comprehensive pytest test coverage (50 tests passing)
- **Multi-Platform Access**: MCP, A2A, and REST API endpoints all functional
- **Real-time Features**: SSE (Server-Sent Events) streaming for live updates
- **Streaming LLM**: Token-by-token streaming with word grouping for optimal UX
- **A2A Protocol Compliance**: Full JSON-RPC 2.0 implementation with streaming support
- **A2A Inspector Integration**: Visual debugging and testing tool for A2A communication
- **API Structure**: Clean separation of concerns across three well-organized API modules

### 🔄 Current Structure
```
yeshuman/
├── README.md               # This specification
├── a2a-inspector/          # A2A debugging and testing tool
│   ├── frontend/           # React frontend for visual testing
│   ├── backend/            # FastAPI backend for A2A communication
│   └── run.sh              # Start script for inspector
└── api/                    # Django + LangGraph backend
    ├── .venv/              # UV virtual environment (Python 3.13.2)
    ├── manage.py           # Django management script
    ├── mcp_client.py       # MCP stdio client for tool integration
    ├── mcp/                # MCP server implementation
    │   ├── server.py       # MCP protocol server logic
    │   ├── api.py          # Django Ninja MCP endpoints (JSON-RPC 2.0)
    │   └── sse.py          # Server-Sent Events support
    ├── a2a/                # Agent-to-Agent communication
    │   ├── models.py       # Django ORM (Agent, A2AMessage, Task, Conversation)
    │   ├── api.py          # A2A JSON-RPC endpoints with streaming
    │   ├── agent_cards.py  # A2A Agent Card specifications
    │   ├── async_tasks.py  # Long-running task management
    │   └── apps.py         # Django app configuration
    ├── agents/             # LangGraph agent implementation
    │   └── agent.py        # ReAct agent with streaming support
    ├── tools/              # Tool implementations
    │   ├── utilities.py    # Calculator, Echo, Weather, Text Analysis
    │   └── agent_tools.py  # Agent Chat, Agent Capabilities
    ├── tests/              # Comprehensive test suite (50 tests)
    │   ├── test_mcp_server.py    # MCP server tests
    │   ├── test_mcp_sse.py       # SSE endpoint tests
    │   ├── test_a2a.py           # A2A protocol tests
    │   ├── test_agent.py         # Agent functionality tests
    │   └── test_api.py           # Main API tests
    └── yeshuman/           # Django project directory
        ├── settings.py     # Django configuration
        ├── urls.py         # URL routing
        ├── api.py          # Main agent chat API
        ├── asgi.py         # ASGI config
        └── wsgi.py         # WSGI config
```

### 🎯 Next Steps
1. **A2A Authentication**: Implement OAuth2 and API key authentication
2. **Enhanced Security**: TLS, rate limiting, and security headers
3. **Production Config**: PostgreSQL, Redis, and deployment settings
4. **Tool Expansion**: Add more LangChain BaseTools to the ecosystem
5. **Performance Optimization**: Caching, database optimization, and scaling
6. **Client SDKs**: Generate client libraries for different programming languages

## Quick Start

### 1. Start the Yes Human Agent Stack

```bash
cd api
source .venv/bin/activate
python manage.py check          # Verify Django setup
python manage.py runserver      # Start development server at http://localhost:3001
```

### 2. Start the A2A Inspector (Optional)

In a separate terminal window:

```bash
# From the root directory
./a2a-inspector/run.sh          # Start A2A Inspector at http://localhost:3000
```

### 3. Test the Stack

```bash
# Test MCP functionality
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | python mcp_client.py

# Test A2A functionality
curl http://localhost:3001/a2a/agent-card/a2a

# Run comprehensive tests
pytest                          # All 50 tests should pass
```

## MCP (Model Context Protocol) Usage

### Overview
The Yes Human stack includes a complete MCP implementation:
- **MCP Server**: Django-hosted server exposing tools via MCP protocol with JSON-RPC 2.0
- **MCP Client**: Stdio-based client for integration with MCP-compatible tools (like Cursor IDE)
- **Available Tools**: Calculator, Echo, Weather, Text Analysis, Agent Chat, and Agent Capabilities
- **Real-time Features**: SSE streaming support for live updates

### Starting the MCP Server

```bash
cd api
source .venv/bin/activate
python manage.py runserver      # Starts Django server on http://localhost:3001
```

The MCP server will be available at `http://localhost:3001/mcp/`

### Using the MCP Client

The MCP client (`mcp_client.py`) provides a stdio interface that MCP-compatible tools expect:

#### Basic Usage
```bash
cd api
source .venv/bin/activate

# List available tools
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "1"}' | python mcp_client.py

# Call calculator tool
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "calculator", "arguments": {"expression": "2 + 3 * 4"}}, "id": "2"}' | python mcp_client.py

# Call echo tool
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "echo", "arguments": {"message": "Hello MCP!"}}, "id": "3"}' | python mcp_client.py
```

#### Expected Responses
```json
// tools/list response
{"result": {"tools": [{"name": "calculator", "description": "Perform basic mathematical calculations...", "inputSchema": {...}}, {"name": "echo", "description": "Echo back any message...", "inputSchema": {...}}]}, "error": null, "id": "1"}

// calculator response
{"result": {"content": [{"type": "text", "text": "Result: 14"}]}, "error": null, "id": "2"}

// echo response
{"result": {"content": [{"type": "text", "text": "Echo: Hello MCP!"}]}, "error": null, "id": "3"}
```

### Available Tools

#### Calculator Tool
- **Name**: `calculator`
- **Description**: Perform basic mathematical calculations
- **Input**: `{"expression": "mathematical_expression"}`
- **Example**: `{"expression": "15 + 25 * 2"}` → `"Result: 65"`

#### Echo Tool
- **Name**: `echo`
- **Description**: Echo back any message
- **Input**: `{"message": "text_to_echo"}`
- **Example**: `{"message": "Hello World"}` → `"Echo: Hello World"`

#### Weather Tool
- **Name**: `weather`
- **Description**: Get current weather information for a location
- **Input**: `{"location": "city_name"}`
- **Example**: `{"location": "London"}` → Mock weather data

#### Text Analysis Tool
- **Name**: `text_analysis`
- **Description**: Analyze text for sentiment, word count, or generate summaries
- **Input**: `{"text": "text_to_analyze", "analysis_type": "summary|sentiment|wordcount"}`
- **Example**: Provides detailed text analysis results

#### Agent Chat Tool
- **Name**: `agent_chat`
- **Description**: Chat directly with the Yes Human LangGraph agent
- **Input**: `{"message": "question_or_request"}`
- **Example**: Direct conversation with your intelligent agent

#### Agent Capabilities Tool
- **Name**: `agent_capabilities`
- **Description**: Get information about the agent's capabilities and features
- **Input**: `{"detail_level": "summary|detailed"}`
- **Example**: Returns comprehensive agent capability information

### Error Handling

The MCP implementation handles various error conditions:

```bash
# Non-existent tool
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "nonexistent", "arguments": {}}, "id": "4"}' | python mcp_client.py
# Response: {"result": null, "error": {"code": -32603, "message": "Tool 'nonexistent' not found"}, "id": "4"}

# Invalid method
echo '{"jsonrpc": "2.0", "method": "invalid/method", "params": {}, "id": "5"}' | python mcp_client.py
# Response: {"result": null, "error": {"code": -32601, "message": "Method not found: invalid/method"}, "id": "5"}
```

### Integration with Cursor IDE

To use with Cursor IDE, configure the MCP client in your Cursor settings:

```json
{
  "mcp": {
    "servers": {
      "yeshuman": {
        "command": "python",
        "args": ["/path/to/yeshuman/api/mcp_client.py"],
        "cwd": "/path/to/yeshuman/api"
      }
    }
  }
}
```

### Direct HTTP API (Alternative)

You can also interact with the MCP server directly via HTTP:

```bash
# List tools
curl -X GET http://localhost:3001/mcp/tools

# Call tool directly
curl -X POST http://localhost:3001/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculator", "arguments": {"expression": "2+2"}}'
```

## A2A (Agent-to-Agent) Communication

### Overview
The Yes Human stack includes a complete A2A server implementation for agent-to-agent communication:
- **JSON-RPC 2.0 Protocol**: Full compliance with A2A specification
- **Streaming Support**: Token-by-token LLM streaming with word grouping
- **Agent Cards**: Structured capability descriptions for discovery
- **Message System**: Asynchronous message passing between agents
- **Task Management**: Task delegation and completion tracking
- **Real-time Updates**: SSE streaming for live message feeds

### Key Features
- **Agent Registration**: Agents can register/unregister dynamically
- **Capability Discovery**: Find agents by specific capabilities
- **Message Queuing**: Persistent message storage and delivery
- **Task Tracking**: Full lifecycle management of delegated tasks
- **Heartbeat System**: Agent presence and health monitoring

### API Endpoints
```bash
# Agent Management
POST /a2a/agents/register          # Register new agent
DELETE /a2a/agents/unregister/{name} # Unregister agent
POST /a2a/agents/{name}/heartbeat  # Update agent heartbeat
GET /a2a/discover                  # Discover available agents

# Agent Cards (A2A Specification Compliance)
GET /a2a/agent-card                # Get Yes Human agent card
GET /a2a/agent-card/{agent_name}   # Get agent card by name
POST /a2a/capability-match         # Match agent capabilities

# Messaging
POST /a2a/messages/send            # Send message to agent
GET /a2a/messages/{agent_id}       # Get agent's messages
POST /a2a/messages/{id}/read       # Mark message as read

# Task Management
POST /a2a/tasks/create             # Create new task
GET /a2a/tasks/{agent_id}          # Get agent's tasks

# Real-time Updates
GET /a2a/stream/{agent_id}         # SSE stream of messages
```

### Agent Cards
Following A2A specification standards, the Yes Human agent provides structured **Agent Cards** that describe:
- **Capabilities**: Detailed specifications with input/output schemas
- **Endpoints**: Available protocols (MCP, A2A, REST) with authentication methods
- **Metadata**: Version, owner, documentation, SLA information  
- **Tags**: Discovery and capability matching
- **Status**: Real-time operational information

Example agent card request:
```bash
curl http://localhost:8000/a2a/agent-card
```

Example capability matching:
```bash
curl -X POST http://localhost:8000/a2a/capability-match \
  -H "Content-Type: application/json" \
  -d '{"required_capabilities": ["calculation"], "required_tags": ["langgraph"]}'
```

### A2A Streaming Protocol

The Yes Human agent supports streaming communication via JSON-RPC 2.0:

#### Non-Streaming Messages
```bash
curl -X POST http://localhost:8000/a2a/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Calculate 25 + 17"}]
      }
    }
  }'
```

#### Streaming Messages (SSE)
```bash
curl -X POST http://localhost:8000/a2a/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1", 
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Tell me about the weather"}]
      }
    }
  }'
```

The streaming response includes:
1. **Initial Task**: Status and context information
2. **Message Chunks**: Word-by-word streaming for optimal UX
3. **Status Updates**: Task completion notifications

## A2A Inspector - Visual Testing Tool

### Overview
The A2A Inspector provides a web-based interface for testing and debugging A2A communication:
- **Visual Chat Interface**: Real-time conversation with streaming support
- **Protocol Validation**: Automatic compliance checking with A2A specification
- **Message Inspection**: Raw JSON-RPC message viewing and debugging
- **Agent Discovery**: Browse and connect to available A2A agents
- **Streaming Support**: Visual representation of token-by-token streaming

### Prerequisites
- Node.js and npm installed
- Python 3.13+ with uv package manager
- Yes Human Agent Stack running on http://localhost:3001

### Installation & Setup

The A2A Inspector is automatically cloned and configured when you first run:

```bash
# From the project root directory
./a2a-inspector/run.sh
```

If you need to manually install:

```bash
# Clone the inspector (if not already present)
git clone https://github.com/a2aproject/a2a-inspector.git

# Install dependencies and start
cd a2a-inspector
uv sync                    # Install Python dependencies
cd frontend && npm install # Install Node.js dependencies
cd .. && chmod +x run.sh   # Make run script executable
./run.sh                   # Start the inspector
```

### Using the A2A Inspector

1. **Start the Yes Human Agent Stack**:
   ```bash
   cd api && source .venv/bin/activate && python manage.py runserver
   ```

2. **Start the A2A Inspector** (in a separate terminal):
   ```bash
   ./a2a-inspector/run.sh
   ```

3. **Open the Inspector**: Navigate to http://localhost:3000

4. **Connect to Yes Human Agent**:
   - Click "Add Agent" or "Connect to Agent"
   - Enter the Agent Card URL: `http://localhost:3001/a2a/agent-card/a2a`
   - Click "Connect"

5. **Test Streaming Communication**:
   - Type a message like "Calculate 25 + 17 and explain the result"
   - Toggle streaming mode to see word-by-word responses
   - Each word/phrase appears as a separate message bubble (A2A protocol compliant)

### Inspector Features

#### Agent Discovery
- **Auto-Detection**: Automatically discovers agents from Agent Card URLs
- **Capability Matching**: Browse agent skills and capabilities
- **Connection Status**: Real-time connection monitoring

#### Message Testing
- **Chat Interface**: Natural conversation flow with the agent
- **Streaming Toggle**: Switch between streaming and non-streaming modes
- **Message Validation**: Automatic A2A protocol compliance checking
- **Raw JSON View**: Inspect underlying JSON-RPC messages

#### Debugging Tools
- **Protocol Inspector**: View raw A2A messages and responses
- **Error Handling**: Clear error messages for debugging
- **Performance Metrics**: Response times and streaming performance
- **Connection Logs**: Detailed communication logs

### Streaming Behavior

When streaming is enabled, you'll see:
- ✅ **Compliant Messages**: Each word/phrase as a separate bubble
- ✅ **Tool Usage Indicators**: "[Using calculator tool...]" messages
- ✅ **Progressive Responses**: Real-time token-by-token delivery
- ✅ **Task Status Updates**: Start/completion notifications

This behavior follows the A2A specification where each message chunk is a separate protocol message.

### Troubleshooting

#### Inspector Won't Start
```bash
# Check if ports are available
lsof -i :3000  # Frontend port
lsof -i :8001  # Backend port

# Restart with clean install
rm -rf a2a-inspector
git clone https://github.com/a2aproject/a2a-inspector.git
cd a2a-inspector && ./run.sh
```

#### Connection Issues
```bash
# Verify Yes Human agent is running
curl http://localhost:3001/a2a/agent-card/a2a

# Check agent card format
curl -s http://localhost:8000/a2a/agent-card/a2a | jq .
```

#### Streaming Not Working
- Ensure both services are running (Django + Inspector)
- Check that `streaming: true` in the agent card capabilities
- Verify browser supports Server-Sent Events

## Testing

### Running All Tests
```bash
cd api
source .venv/bin/activate
pytest                         # Run all tests
pytest -v                      # Verbose output
pytest tests/test_mcp_server.py # Run specific test file
```

### Test Coverage (50 Tests Passing)
- **MCP Server Tests**: Protocol compliance, tool execution, error handling
- **MCP SSE Tests**: Server-Sent Events functionality  
- **A2A Tests**: Agent registration, discovery, messaging, task management, streaming
- **Agent Tests**: LangGraph agent functionality and tool integration
- **API Tests**: Django Ninja endpoint testing
- **Tool Tests**: Individual tool functionality and validation
- **Streaming Tests**: Token-by-token streaming and word grouping validation

### Continuous Testing
```bash
cd api
source .venv/bin/activate
ptw                            # Watch for changes and run tests automatically
```

## Development Commands

```bash
# Activate environment
cd api && source .venv/bin/activate

# Install new packages
uv pip install package-name

# Django management
python manage.py check
python manage.py migrate
python manage.py runserver

# Testing
pytest                         # Run all tests (50 tests)
pytest -v                      # Verbose testing
ptw                           # Watch mode testing

# MCP client testing
python mcp_client.py          # Interactive MCP client (expects stdin)
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | python mcp_client.py

# A2A testing
curl -X GET http://localhost:3001/a2a/discover
curl -X GET http://localhost:3001/a2a/agent-card/a2a
curl -X POST http://localhost:3001/a2a/capability-match -H "Content-Type: application/json" -d '{"required_capabilities": ["calculation"]}'

# A2A streaming testing
curl -X POST http://localhost:3001/a2a/ -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": "1", "method": "message/send", "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": "Hello!"}]}}}'

# A2A Inspector testing
./a2a-inspector/run.sh        # Start visual testing tool at http://localhost:3000
```
