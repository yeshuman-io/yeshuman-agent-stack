# Yes Human Labs UI

A sophisticated streaming interface for the Yes Human Agent Stack, featuring real-time parallel streaming of thinking, voice, tools, and structured data.

## 🎯 Features

- **Multi-Stream Interface**: Parallel thinking + voice + tools + structured data
- **Anthropic SSE Protocol**: Compatible with Claude-style streaming events
- **JSON Delta Accumulation**: Progressive JSON fragment streaming and parsing
- **Real-time Updates**: Live content streaming with auto-scrolling
- **Responsive Design**: Mobile-friendly tabs + desktop multi-column layout
- **Dark/Light Themes**: Professional UI with theme switching

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- pnpm 9+
- Yes Human Agent Stack running on `localhost:8111`

### Installation

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Open browser to http://localhost:3000
```

### Build for Production

```bash
# Type check
pnpm type-check

# Build
pnpm build

# Preview build
pnpm preview
```

## 🎼 Architecture Integration

This UI connects to your Yes Human Agent Stack's `/agent/stream` endpoint and expects Anthropic-compatible SSE events:

```typescript
// Thinking stream
{
  "event": "content_block_delta",
  "data": {
    "index": 0,
    "delta": {
      "type": "thinking_delta",
      "text": "Analyzing your request..."
    }
  }
}

// Voice stream  
{
  "event": "content_block_delta",
  "data": {
    "index": 1,
    "delta": {
      "type": "voice_delta", 
      "text": "Hmm, interesting question..."
    }
  }
}

// JSON fragment stream
{
  "event": "content_block_delta",
  "data": {
    "index": 2,
    "delta": {
      "type": "json_delta",
      "text": "{\"analysis\": \"This"
    }
  }
}
```

## 🎨 UI Panels

- **Main Chat**: Primary conversation interface
- **Thinking**: Real-time reasoning display
- **Voice**: Audio-ready speech fragments
- **Tools**: Tool usage and results
- **Knowledge**: Structured data and JSON accumulation
- **System**: Connection status and notifications

## 🛠️ Development

```bash
# Install dependencies
pnpm install

# Start dev server with hot reload
pnpm dev

# Run linting
pnpm lint

# Type checking
pnpm type-check
```

## 📦 Tech Stack

- **React 19** + **TypeScript**
- **Vite** for fast development
- **Tailwind CSS** for styling
- **Radix UI** for components
- **Microsoft Fetch Event Source** for SSE
- **Lucide React** for icons

## 🔗 Integration

The UI automatically connects to your Yes Human Agent Stack. Make sure your agent server is running with the parallel streaming conductor node for the full experience.