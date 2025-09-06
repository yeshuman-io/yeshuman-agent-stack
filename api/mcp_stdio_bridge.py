#!/usr/bin/env python
"""
MCP Stdio to HTTP Bridge for Cursor integration.
Converts stdio MCP protocol to HTTP requests for Django MCP server.
"""
import asyncio
import json
import sys
import logging
import aiohttp
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MCPStdioToHTTPBridge:
    """Bridge between stdio MCP protocol and HTTP MCP server."""

    def __init__(self, http_url: str = "http://127.0.0.1:8000/mcp/"):
        self.http_url = http_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def forward_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Forward MCP request to HTTP server."""
        try:
            logger.debug(f"Forwarding request: {json.dumps(request_data, indent=2)}")

            async with self.session.post(
                self.http_url,
                json=request_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'MCP-Bridge/1.0.0'
                }
            ) as response:
                response_text = await response.text()
                logger.debug(f"HTTP Response: {response.status} - {response_text}")

                if response.status == 200:
                    return json.loads(response_text)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"HTTP error: {response.status}"
                        },
                        "id": request_data.get("id")
                    }

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Bridge error: {str(e)}"
                },
                "id": request_data.get("id")
            }

    async def handle_stdio(self):
        """Handle stdio communication with Cursor MCP client."""
        logger.info("Starting MCP stdio bridge...")

        try:
            # Read from stdin line by line
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                logger.debug(f"Received line: {line}")

                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)
                    logger.info(f"Parsed request: {request}")

                    # Forward to HTTP server
                    response = await self.forward_request(request)

                    # Send response back via stdout
                    response_json = json.dumps(response)
                    print(response_json, flush=True)
                    logger.debug(f"Sent response: {response_json}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            logger.info("Bridge interrupted")
        except Exception as e:
            logger.error(f"Bridge error: {e}")

async def main():
    """Main bridge function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async with MCPStdioToHTTPBridge() as bridge:
        await bridge.handle_stdio()

if __name__ == "__main__":
    asyncio.run(main())

