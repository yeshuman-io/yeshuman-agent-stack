#!/usr/bin/env python3
"""
Simple MCP client that bridges to our Django hosted MCP server.
This provides the stdio interface that MCP clients like Cursor expect.
"""
import sys
import json
import urllib.request
import urllib.parse
import socket

def main():
    """Main MCP client function."""
    base_url = "http://localhost:8000/mcp/"
    
    try:
        # Handle stdin input
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request_data = json.loads(line)
                
                # Create HTTP request with timeout
                data = json.dumps(request_data).encode('utf-8')
                req = urllib.request.Request(
                    base_url,
                    data=data,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Yes Human-MCP-Client/1.0'
                    }
                )
                
                # Send request with timeout handling
                try:
                    with urllib.request.urlopen(req, timeout=30) as response:
                        response_data = json.loads(response.read().decode('utf-8'))
                        print(json.dumps(response_data), flush=True)
                except socket.timeout:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": "Request timed out"
                        },
                        "id": request_data.get("id")
                    }
                    print(json.dumps(error_response), flush=True)
                    
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Client error: {str(e)}"
                    },
                    "id": request_data.get("id") if 'request_data' in locals() else None
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
