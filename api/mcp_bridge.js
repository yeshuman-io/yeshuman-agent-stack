#!/usr/bin/env node

/**
 * MCP Bridge: Connects HTTP MCP server to stdio for Claude Desktop
 */

const http = require('http');
const https = require('https');

class MCPBridge {
    constructor(serverUrl) {
        this.serverUrl = serverUrl;
        console.error('🔧 MCP Bridge initialized with server:', serverUrl);
    }

    async handleMessage(message) {
        try {
            console.error('📨 Received message:', JSON.stringify(message, null, 2));

            const url = new URL(this.serverUrl);
            const options = {
                hostname: url.hostname,
                port: url.port || (url.protocol === 'https:' ? 443 : 80),
                path: '/mcp',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'User-Agent': 'MCP-Bridge/1.0'
                }
            };

            return new Promise((resolve, reject) => {
                const client = url.protocol === 'https:' ? https : http;
                const req = client.request(options, (res) => {
                    let data = '';

                    console.error('📡 HTTP Response status:', res.statusCode);
                    console.error('📡 HTTP Response headers:', res.headers);

                    res.on('data', (chunk) => {
                        data += chunk;
                        console.error('📦 Received chunk:', chunk.toString());
                    });

                    res.on('end', () => {
                        console.error('✅ HTTP Response complete:', data);
                        try {
                            const response = JSON.parse(data);
                            resolve(response);
                        } catch (e) {
                            console.error('❌ Failed to parse response:', e);
                            reject(new Error('Invalid JSON response from server'));
                        }
                    });
                });

                req.on('error', (e) => {
                    console.error('❌ HTTP Request error:', e);
                    reject(e);
                });

                req.write(JSON.stringify(message));
                req.end();
            });

        } catch (error) {
            console.error('💥 Error handling message:', error);
            return {
                jsonrpc: '2.0',
                error: {
                    code: -32603,
                    message: `Bridge error: ${error.message}`
                },
                id: message.id
            };
        }
    }
}

// Main stdio loop
async function main() {
    const serverUrl = process.argv[2] || 'http://localhost:8000';

    console.error('🚀 Starting MCP Bridge...');
    const bridge = new MCPBridge(serverUrl);

    process.stdin.setEncoding('utf8');

    let buffer = '';
    process.stdin.on('data', async (chunk) => {
        buffer += chunk;

        // Try to parse complete JSON-RPC messages
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
            if (line.trim()) {
                try {
                    const message = JSON.parse(line.trim());
                    console.error('🎯 Processing message:', message);

                    const response = await bridge.handleMessage(message);

                    // Send response back to Claude Desktop
                    const responseStr = JSON.stringify(response) + '\n';
                    process.stdout.write(responseStr);
                    console.error('📤 Sent response:', responseStr);

                } catch (e) {
                    console.error('❌ Failed to parse message:', e);
                    console.error('   Raw line:', line);
                }
            }
        }
    });

    process.stdin.on('end', () => {
        console.error('🔚 Stdin ended, exiting...');
        process.exit(0);
    });

    console.error('✅ MCP Bridge ready for messages...');
}

if (require.main === module) {
    main().catch((error) => {
        console.error('💥 Fatal error:', error);
        process.exit(1);
    });
}

module.exports = MCPBridge;
