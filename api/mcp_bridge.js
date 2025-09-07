#!/usr/bin/env node

/**
 * MCP Bridge: Connects HTTP MCP server to stdio for Claude Desktop
 */

const http = require('http');
const https = require('https');

class MCPBridge {
    constructor(serverUrl) {
        this.serverUrl = serverUrl;
        this.agent = new https.Agent({
            keepAlive: true,
            keepAliveMsecs: 30000,
            maxSockets: 10,
            maxFreeSockets: 5,
            timeout: 90000
        });
        this.circuitBreaker = {
            failures: 0,
            lastFailureTime: 0,
            state: 'CLOSED', // CLOSED, OPEN, HALF_OPEN
            failureThreshold: 3,
            recoveryTimeout: 30000
        };
        console.error('🔧 MCP Bridge initialized with server:', serverUrl);
        console.error('🔄 Connection pooling enabled with 90s timeout');

        // Start connection warming
        this.startConnectionWarming();
    }

    startConnectionWarming() {
        // Warm up connection every 5 minutes to prevent Railway cold starts
        setInterval(async () => {
            try {
                console.error('🔥 Warming up connection...');
                const isHealthy = await this.checkHealth();
                if (isHealthy) {
                    console.error('✅ Connection warm - server ready');
                } else {
                    console.error('❌ Connection warming failed - server may be down');
                }
            } catch (error) {
                console.error('❌ Connection warming error:', error.message);
            }
        }, 5 * 60 * 1000); // 5 minutes

        console.error('🕒 Connection warming scheduled every 5 minutes');
    }

    async checkHealth() {
        return new Promise((resolve, reject) => {
            const url = new URL(this.serverUrl);
            const options = {
                hostname: url.hostname,
                port: url.port || (url.protocol === 'https:' ? 443 : 80),
                path: '/ping',
                method: 'GET',
                timeout: 5000, // 5 second timeout for health check
                agent: this.agent
            };

            const client = url.protocol === 'https:' ? https : http;
            const req = client.request(options, (res) => {
                if (res.statusCode === 200) {
                    resolve(true);
                } else {
                    resolve(false);
                }
            });

            req.on('error', () => resolve(false));
            req.on('timeout', () => {
                req.destroy();
                resolve(false);
            });

            req.end();
        });
    }

    updateCircuitBreaker(success) {
        if (success) {
            this.circuitBreaker.failures = 0;
            this.circuitBreaker.state = 'CLOSED';
        } else {
            this.circuitBreaker.failures++;
            this.circuitBreaker.lastFailureTime = Date.now();

            if (this.circuitBreaker.failures >= this.circuitBreaker.failureThreshold) {
                this.circuitBreaker.state = 'OPEN';
                console.error('🔴 Circuit breaker OPEN - too many failures');
            }
        }
    }

    async handleMessage(message) {
        try {
            console.error('📨 Received message:', JSON.stringify(message, null, 2));

            // Check circuit breaker state
            if (this.circuitBreaker.state === 'OPEN') {
                const timeSinceLastFailure = Date.now() - this.circuitBreaker.lastFailureTime;
                if (timeSinceLastFailure < this.circuitBreaker.recoveryTimeout) {
                    console.error('⛔ Circuit breaker OPEN - rejecting request');
                    return {
                        jsonrpc: '2.0',
                        error: {
                            code: -32003,
                            message: 'Service temporarily unavailable - circuit breaker open'
                        },
                        id: message.id
                    };
                } else {
                    console.error('🔄 Circuit breaker HALF_OPEN - attempting recovery');
                    this.circuitBreaker.state = 'HALF_OPEN';
                }
            }

            // Check server health first
            console.error('🏥 Checking server health...');
            const isHealthy = await this.checkHealth();
            if (!isHealthy) {
                console.error('❌ Server health check failed');
                this.updateCircuitBreaker(false);
                return {
                    jsonrpc: '2.0',
                    error: {
                        code: -32001,
                        message: 'Server health check failed - service may be starting up'
                    },
                    id: message.id
                };
            }
            console.error('✅ Server health check passed');

            // Retry logic with exponential backoff
            let lastError;
            for (let attempt = 1; attempt <= 3; attempt++) {
                try {
                    console.error(`🔄 Attempt ${attempt}/3`);
                    const result = await this.makeRequest(message);
                    this.updateCircuitBreaker(true);
                    return result;
                } catch (error) {
                    lastError = error;
                    console.error(`❌ Attempt ${attempt} failed:`, error.message);

                    if (attempt < 3) {
                        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                        console.error(`⏳ Waiting ${delay}ms before retry...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                }
            }

            // All retries failed
            this.updateCircuitBreaker(false);
            return {
                jsonrpc: '2.0',
                error: {
                    code: -32002,
                    message: `Request failed after 3 attempts: ${lastError.message}`
                },
                id: message.id
            };

        } catch (error) {
            console.error('❌ Unexpected error in handleMessage:', error);
            this.updateCircuitBreaker(false);
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

    async makeRequest(message) {
        return new Promise((resolve, reject) => {
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
                },
                agent: this.agent // Use connection pooling agent
            };

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

                            // Send a more compatible error response for Claude Desktop
                            const errorResponse = {
                                jsonrpc: '2.0',
                                error: {
                                    code: -32700,
                                    message: 'Parse error: Invalid JSON response from server'
                                },
                                id: message.id
                            };
                            console.error('📤 Sending parse error response:', JSON.stringify(errorResponse));
                            resolve(errorResponse); // Resolve instead of reject to send error to Claude
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
                    console.error('❌ Error code:', e.code);
                    reject(new Error(`${e.code || 'UNKNOWN'}: ${e.message}`));
                });

                // Handle request timeout
                req.setTimeout(90000, () => {
                    console.error('⏰ Request timeout after 90 seconds');
                    req.destroy();
                    reject(new Error('Request timeout after 90 seconds'));
                });

                const messageData = JSON.stringify(message);
                console.error('📤 Sending request data:', messageData);
                req.write(messageData);
                req.end();
            });
        });
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

        // Add Railway-specific logging
        if (serverUrl.includes('railway.app')) {
            console.error('🚂 Railway Mode: Enabled with 90-second cold start timeout');
        }
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

            // Send error response with proper format for Claude Desktop
            const errorResponse = {
                jsonrpc: '2.0',
                error: {
                    code: -32603,
                    message: `Bridge processing error: ${e.message}`
                },
                id: message.id || null
            };

            console.error('📤 Sending processing error response:', JSON.stringify(errorResponse));

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
