# Yes Human API

Django + LangGraph API backend for the Yes Human Agent Stack.

## Quick Start

```bash
# Install dependencies
uv sync

# Activate virtual environment  
source .venv/bin/activate

# Run development server
./manage.py runserver

# Or with explicit port
./manage.py runserver 8111
```

## Testing

```bash
# Run all tests
uv run pytest

# Run tests with watch mode
uv run ptw

# Run specific test file
uv run pytest tests/test_auth.py -v
```

## 🔑 API Key Authentication

Environment variable-based API key authentication for secure access.

### Configuration

```bash
# .env file
A2A_API_KEYS=inspector:dev-inspector-key-123,agent1:agent-key-456
MCP_API_KEY=mcp-dev-key-abc123
A2A_AUTH_ENABLED=True
MCP_AUTH_ENABLED=True
```

### Usage in Views

```python
from apps.accounts import require_a2a_auth, require_mcp_auth

@require_a2a_auth
def my_a2a_endpoint(request):
    client_name = request.user.client_name  # "inspector"
    return {"message": f"Hello {client_name}"}

@require_mcp_auth  
def my_mcp_endpoint(request):
    return {"status": "authenticated"}
```

### Client Usage

```bash
# A2A requests
curl -H "X-API-Key: dev-inspector-key-123" http://localhost:8111/a2a/

# MCP requests  
curl -H "X-API-Key: mcp-dev-key-abc123" http://localhost:8111/mcp/
```

## 🚀 API Endpoints

### A2A (Agent-to-Agent) Protocol
- **Base URL**: `/a2a/`
- **Authentication**: A2A API keys
- **Format**: JSON-RPC 2.0
- **Features**: Agent registration, messaging, task management

### MCP (Model Context Protocol)
- **Base URL**: `/mcp/`
- **Authentication**: MCP API key
- **Format**: JSON-RPC 2.0
- **Features**: Tool access, server communication

### Custom Agent UI
- **Base URL**: `/agent/`
- **Authentication**: None (development)
- **Format**: Server-Sent Events (Anthropic Delta)
- **Features**: Real-time streaming, multi-panel display

## 🏗️ Architecture

### Core Components

```
api/
├── agent/           # Custom LangGraph agent
│   ├── api.py      # Agent streaming endpoints
│   └── graph.py    # LangGraph workflow
├── a2a/            # Agent-to-Agent protocol
│   ├── api.py      # A2A endpoints
│   └── models.py   # Agent/Message models
├── mcp/            # Model Context Protocol
│   ├── api.py      # MCP endpoints
│   └── server.py   # MCP server implementation
├── auth/           # Simple API key authentication
│   ├── backends.py # Django auth backends
│   └── middleware.py # Auth middleware
├── streaming/      # Multi-consumer streaming
│   ├── generators.py # Anthropic SSE generator
│   └── service.py   # Universal streaming service
└── utils/          # Shared utilities
    └── sse.py      # SSE response helpers
```

### Authentication Flow

1. **Client Request**: Include `X-API-Key` header
2. **Django Middleware**: Automatically authenticate using backends
3. **Request Processing**: `request.user` contains `APIKeyUser` instance
4. **Response**: Protected endpoints return data or 401/403 errors

## 🧪 Development

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
vim .env
```

### Key Environment Variables

```bash
# Authentication
A2A_API_KEYS=client1:key1,client2:key2
MCP_API_KEY=mcp-secret-key
A2A_AUTH_ENABLED=True
MCP_AUTH_ENABLED=True

# OpenAI API
OPENAI_API_KEY=your-openai-key

# Django
DEBUG=True
SECRET_KEY=your-secret-key
```

### Adding New API Keys

1. **Add to environment**:
   ```bash
   # For A2A clients
   A2A_API_KEYS=existing:key1,newclient:new-key-123
   
   # For MCP (single key)
   MCP_API_KEY=new-mcp-key
   ```

2. **Restart server** to pick up changes

3. **Test access**:
   ```bash
   curl -H "X-API-Key: new-key-123" http://localhost:8111/a2a/
   ```

## 📁 File Structure

```
api/
├── agent/                    # Custom agent implementation
├── a2a/                     # A2A protocol endpoints
├── auth/                    # Simple authentication
│   ├── __init__.py         # Clean exports
│   ├── backends.py         # Environment-based auth
│   └── middleware.py       # Django middleware
├── mcp/                    # MCP protocol endpoints
├── streaming/              # Multi-consumer streaming
├── tests/                  # Test suite
├── tools/                  # Agent tools
├── utils/                  # Shared utilities
├── yeshuman/              # Django project settings
├── manage.py              # Django management
├── .env                   # Environment configuration
├── pytest.ini            # Test configuration
└── README.md             # This file
```

## ✨ Features

- ✅ **Simple Authentication** - Environment variable-based API keys
- ✅ **Multi-Protocol** - A2A, MCP, and custom streaming endpoints
- ✅ **Real-time Streaming** - Server-Sent Events with Anthropic Delta format
- ✅ **LangGraph Integration** - Custom agent workflows with thinking/response nodes
- ✅ **Django Framework** - Production-ready web framework
- ✅ **Comprehensive Testing** - Full test suite with pytest
- ✅ **Hot Reloading** - Development server with automatic restarts

## 🚦 Getting Started

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd yeshuman/api
   uv sync
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run development**:
   ```bash
   source .venv/bin/activate
   ./manage.py runserver 8111
   ```

4. **Test authentication**:
   ```bash
   curl -H "X-API-Key: dev-inspector-key-123" http://localhost:8111/a2a/
   ```

That's it! You now have a fully functional API server with authentication, streaming, and multi-protocol support. 🎉