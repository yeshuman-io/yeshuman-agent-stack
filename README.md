# YesHuman Agent Stack

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
- **Project Structure**: Basic Django project created in `/api` directory
- **MCP Server**: Model Context Protocol server implementation with Django Ninja
- **MCP Client**: Stdio-based MCP client for integration with MCP-compatible tools
- **Tool System**: LangChain BaseTool integration with calculator and echo tools
- **Testing Suite**: Comprehensive pytest test coverage for MCP functionality

### 🔄 Current Structure
```
yeshuman/
├── README.md               # This specification
└── api/                    # Django + LangGraph backend
    ├── .venv/              # UV virtual environment (Python 3.13.2)
    ├── manage.py           # Django management script
    ├── mcp_client.py       # MCP stdio client for tool integration
    ├── mcp/                # MCP server implementation
    │   ├── server.py       # MCP protocol server logic
    │   ├── api.py          # Django Ninja MCP endpoints
    │   └── sse.py          # Server-Sent Events support
    ├── tools/              # Tool implementations
    │   └── utilities.py    # Calculator and echo tools
    ├── tests/              # Test suite
    │   ├── test_mcp_server.py    # MCP server tests
    │   └── test_mcp_sse.py       # SSE endpoint tests
    └── yeshuman/           # Django project directory
        ├── settings.py     # Django configuration
        ├── urls.py         # URL routing
        ├── asgi.py         # ASGI config
        └── wsgi.py         # WSGI config
```

### 🎯 Next Steps
1. Add essential dependencies (LangGraph, PostgreSQL)
2. Configure Django settings for production readiness
3. Create Django apps structure (core, api, etc.)
4. Implement basic LangGraph agent
5. Add A2A server capabilities
6. Set up synthetic data generation

## Quick Start

```bash
cd api
source .venv/bin/activate
python manage.py check          # Verify Django setup
python manage.py runserver      # Start development server
```

## MCP (Model Context Protocol) Usage

### Overview
The YesHuman stack includes a complete MCP implementation:
- **MCP Server**: Django-hosted server exposing tools via MCP protocol
- **MCP Client**: Stdio-based client for integration with MCP-compatible tools (like Cursor IDE)
- **Available Tools**: Calculator and Echo tools with full schema validation

### Starting the MCP Server

```bash
cd api
source .venv/bin/activate
python manage.py runserver      # Starts Django server on http://localhost:8000
```

The MCP server will be available at `http://localhost:8000/mcp/`

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
curl -X GET http://localhost:8000/mcp/tools

# Call tool directly
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculator", "arguments": {"expression": "2+2"}}'
```

## Testing

### Running All Tests
```bash
cd api
source .venv/bin/activate
pytest                         # Run all tests
pytest -v                      # Verbose output
pytest tests/test_mcp_server.py # Run specific test file
```

### Test Coverage
- **MCP Server Tests**: Protocol compliance, tool execution, error handling
- **MCP SSE Tests**: Server-Sent Events functionality
- **Tool Tests**: Individual tool functionality and validation
- **API Tests**: Django Ninja endpoint testing

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
pytest                         # Run all tests
pytest -v                      # Verbose testing
ptw                           # Watch mode testing

# MCP client testing
python mcp_client.py          # Interactive MCP client (expects stdin)
```
