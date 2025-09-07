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
                    'User-Agent': 'MCP-Bridge/1.0',
                    'Accept': 'application/json'
                }
            };

            return new Promise((resolve, reject) => {
                const client = url.protocol === 'https:' ? https : http;
                const req = client.request(options, (res) => {
                    let data = '';

                    console.error('📡 HTTP Response status:', res.statusCode);
                    console.error('📡 HTTP Response headers:', JSON.stringify(res.headers, null, 2));

                    res.on('data', (chunk) => {
                        const chunkStr = chunk.toString();
                        data += chunkStr;
                        console.error('📦 Received chunk:', chunkStr);
                    });

                    res.on('end', () => {
                        console.error('✅ HTTP Response complete, total length:', data.length);
                        console.error('✅ Raw response data:', data);

                        // Handle empty response
                        if (!data.trim()) {
                            console.error('⚠️ Empty response from server');
                            resolve({
                                jsonrpc: '2.0',
                                error: {
                                    code: -32603,
                                    message: 'Empty response from server'
                                },
                                id: message.id
                            });
                            return;
                        }

                        try {
                            const response = JSON.parse(data);
                            console.error('✅ Parsed response:', JSON.stringify(response, null, 2));
                            resolve(response);
                        } catch (e) {
                            console.error('❌ Failed to parse JSON response:', e.message);
                            console.error('❌ Raw response that failed to parse:', data);
                            reject(new Error(`Invalid JSON response from server: ${e.message}`));
                        }
                    });

                    // Handle response errors
                    res.on('error', (e) => {
                        console.error('❌ HTTP Response error:', e);
                        reject(new Error(`HTTP response error: ${e.message}`));
                    });
                });

                req.on('error', (e) => {
                    console.error('❌ HTTP Request error:', e);
                    reject(new Error(`HTTP request error: ${e.message}`));
                });

                // Handle request timeout
                req.setTimeout(10000, () => {
                    console.error('⏰ Request timeout after 10 seconds');
                    req.destroy();
                    reject(new Error('Request timeout after 10 seconds'));
                });

                const messageData = JSON.stringify(message);
                console.error('📤 Sending request data:', messageData);
                req.write(messageData);
                req.end();
            });

        } catch (error) {
            console.error('💥 Error in handleMessage:', error);
            console.error('💥 Stack trace:', error.stack);
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
    console.error('🔗 Server URL:', serverUrl);

    let bridge;
    try {
        bridge = new MCPBridge(serverUrl);
        console.error('✅ MCP Bridge initialized successfully');
    } catch (e) {
        console.error('❌ Failed to initialize MCP Bridge:', e);
        process.exit(1);
    }

    process.stdin.setEncoding('utf8');

    let buffer = '';
    let messageQueue = [];
    let processing = false;

    // Process messages sequentially to avoid race conditions
    async function processNextMessage() {
        if (processing || messageQueue.length === 0) {
            return;
        }

        processing = true;
        const message = messageQueue.shift();

        try {
            console.error('🎯 Processing message:', JSON.stringify(message, null, 2));

            const response = await bridge.handleMessage(message);

            // Send response back to Claude Desktop
            const responseStr = JSON.stringify(response) + '\n';
            console.error('📤 Sending response:', responseStr);

            // Ensure stdout is written synchronously
            if (process.stdout.write(responseStr)) {
                console.error('✅ Response sent successfully');
            } else {
                console.error('⚠️ Response buffered, waiting for drain...');
                process.stdout.once('drain', () => {
                    console.error('✅ Response sent after drain');
                });
            }

        } catch (e) {
            console.error('❌ Error processing message:', e);
            console.error('❌ Stack trace:', e.stack);

            // Send error response
            const errorResponse = {
                jsonrpc: '2.0',
                error: {
                    code: -32603,
                    message: `Bridge processing error: ${e.message}`
                },
                id: message.id || null
            };

            try {
                const errorStr = JSON.stringify(errorResponse) + '\n';
                process.stdout.write(errorStr);
                console.error('📤 Sent error response:', errorStr);
            } catch (sendError) {
                console.error('❌ Failed to send error response:', sendError);
            }
        } finally {
            processing = false;
            // Process next message if any
            setImmediate(processNextMessage);
        }
    }

    process.stdin.on('data', (chunk) => {
        console.error('📦 Received chunk, length:', chunk.length);
        buffer += chunk;

        // Try to parse complete JSON-RPC messages
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
            if (line.trim()) {
                try {
                    const message = JSON.parse(line.trim());
                    console.error('✅ Parsed message:', message.method, 'id:', message.id);
                    messageQueue.push(message);
                    processNextMessage();
                } catch (e) {
                    console.error('❌ JSON parse error:', e.message);
                    console.error('❌ Raw input:', line.substring(0, 100));
                }
            }
        }
    });

    process.stdin.on('end', () => {
        console.error('🔚 Stdin ended, exiting gracefully...');
        process.exit(0);
    });

    // Handle process termination signals
    process.on('SIGINT', () => {
        console.error('🛑 Received SIGINT, exiting...');
        process.exit(0);
    });

    process.on('SIGTERM', () => {
        console.error('🛑 Received SIGTERM, exiting...');
        process.exit(0);
    });

    // Handle uncaught exceptions
    process.on('uncaughtException', (err) => {
        console.error('💥 Uncaught exception:', err);
        console.error('💥 Stack trace:', err.stack);
        process.exit(1);
    });

    process.on('unhandledRejection', (reason, promise) => {
        console.error('💥 Unhandled rejection at:', promise, 'reason:', reason);
        process.exit(1);
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
