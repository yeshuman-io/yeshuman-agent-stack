#!/bin/bash

# MCP Bridge Launcher for WSL
# This script translates paths and launches the Node.js bridge

echo "🚀 Starting MCP Bridge Launcher..." >&2
echo "📋 Arguments: $*" >&2

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to the Node.js bridge
BRIDGE_PATH="$SCRIPT_DIR/mcp_bridge.js"

echo "📍 Script dir: $SCRIPT_DIR" >&2
echo "📍 Bridge path: $BRIDGE_PATH" >&2
echo "🔗 Server URL: $1" >&2

# Check if the bridge file exists
if [ ! -f "$BRIDGE_PATH" ]; then
    echo "❌ Bridge file not found: $BRIDGE_PATH" >&2
    ls -la "$SCRIPT_DIR" >&2
    exit 1
fi

echo "✅ Bridge file found" >&2

# Check if Node.js is available - try multiple locations
NODE_PATH=""
NODE_VERSION=""

# Try NVM first (most reliable), then PATH, then system locations
if [ -x "/home/daryl/.nvm/versions/node/v22.17.0/bin/node" ]; then
    NODE_PATH="/home/daryl/.nvm/versions/node/v22.17.0/bin/node"
    NODE_VERSION=$($NODE_PATH --version 2>/dev/null || echo "v22.17.0")
    echo "✅ Node.js found in NVM: $NODE_VERSION" >&2
elif command -v node &> /dev/null; then
    NODE_PATH="node"
    NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
    echo "✅ Node.js found in PATH: $NODE_VERSION" >&2
elif [ -x "/usr/bin/node" ]; then
    NODE_PATH="/usr/bin/node"
    NODE_VERSION=$($NODE_PATH --version 2>/dev/null || echo "system")
    echo "✅ Node.js found in /usr/bin: $NODE_VERSION" >&2
elif [ -x "/usr/local/bin/node" ]; then
    NODE_PATH="/usr/local/bin/node"
    NODE_VERSION=$($NODE_PATH --version 2>/dev/null || echo "local")
    echo "✅ Node.js found in /usr/local/bin: $NODE_VERSION" >&2
else
    echo "❌ Node.js not found in any location" >&2
    echo "🔍 Searched locations (in priority order):" >&2
    echo "  1. NVM: /home/daryl/.nvm/versions/node/v22.17.0/bin/node" >&2
    echo "  2. PATH: $(which node 2>/dev/null || echo 'not found')" >&2
    echo "  3. System: /usr/bin/node" >&2
    echo "  4. Local: /usr/local/bin/node" >&2
    echo "💡 Try installing Node.js: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash" >&2
    exit 1
fi

echo "🚀 Launching Node.js bridge with: $NODE_PATH" >&2
exec "$NODE_PATH" "$BRIDGE_PATH" "$1"
