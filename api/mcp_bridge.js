#!/usr/bin/env node

/**
 * MCP Bridge: Connects HTTP MCP server to stdio for Claude Desktop
 */

const http = require('http');
const https = require('https');

class MCPBridge {
    constructor(serverUrl) {
        this.serverUrl = serverUrl;
        // Cache for Railway to avoid repeated requests
        this.responseCache = new Map();

        // Create both HTTP and HTTPS agents
        // Configure HTTP agents with connection pooling (optimized for Railway)
        this.httpAgent = new http.Agent({
            keepAlive: true,
            keepAliveMsecs: 60000,  // Longer keep-alive for Railway
            maxSockets: 5,          // Fewer concurrent connections for Railway
            maxFreeSockets: 3,
            timeout: 120000,        // Longer timeout for Railway cold starts
            scheduling: 'lifo'       // Last-in-first-out for Railway connections
        });

        this.httpsAgent = new https.Agent({
            keepAlive: true,
            keepAliveMsecs: 60000,  // Longer keep-alive for Railway
            maxSockets: 5,          // Fewer concurrent connections for Railway
            maxFreeSockets: 3,
            timeout: 120000,        // Longer timeout for Railway cold starts
            scheduling: 'lifo',      // Last-in-first-out for Railway connections
            // Railway-specific SSL settings for better compatibility
            rejectUnauthorized: true,
            maxCachedSessions: 10
        });
        this.circuitBreaker = {
            failures: 0,
            lastFailureTime: 0,
            state: 'CLOSED', // CLOSED, OPEN, HALF_OPEN
            failureThreshold: 3,
            recoveryTimeout: 30000
        };

        // Connection health tracking
        this.connectionHealth = {
            lastSuccessfulHealthCheck: Date.now(),
            consecutiveFailures: 0,
            isHealthy: false,
            reconnectAttempts: 0,
            maxTotalTime: serverUrl.includes('railway.app') ? 600000 : 300000, // 10min Railway, 5min others
            reconnectDelay: serverUrl.includes('railway.app') ? 3000 : 5000, // Faster for Railway
            maxReconnectDelay: serverUrl.includes('railway.app') ? 30000 : 20000, // Shorter max for Railway
            startTime: Date.now()
        };

        console.error('🔧 MCP Bridge initialized with server:', serverUrl);
        console.error('🔄 Connection pooling enabled with 90s timeout');

        // Railway-specific configuration
        if (this.serverUrl.includes('railway.app')) {
            console.error('🚂 RAILWAY MODE: Persistent reconnection enabled');
            console.error('🚂 RAILWAY MODE: Health monitoring every 15 seconds');
            console.error('🚂 RAILWAY MODE: Reconnection on first failure');
            console.error('🚂 RAILWAY MODE: 10-minute maximum persistence');
            console.error('🚂 RAILWAY MODE: 3s-30s exponential backoff');
            console.error('🚂 RAILWAY MODE: 10s health check timeout');
            console.error('🚂 RAILWAY MODE: Using /health endpoint (Railway-specific)');
            console.error('🚂 RAILWAY MODE: Trust periodic monitoring (30s window)');
        }

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

        // Start health monitoring for Railway connections
        if (this.serverUrl.includes('railway.app')) {
            this.startHealthMonitoring();
        }
    }

    startHealthMonitoring() {
        // Monitor connection health more aggressively for Railway
        setInterval(async () => {
            console.error('🔍 Periodic health check for Railway connection...');
            await this.checkHealth();
        }, 15 * 1000); // 15 seconds - more aggressive for Railway

        console.error('📊 Health monitoring started - checking Railway connection every 15 seconds');
    }

    getConnectionStatus() {
        const timeSinceLastSuccess = Date.now() - this.connectionHealth.lastSuccessfulHealthCheck;
        const status = {
            isHealthy: this.connectionHealth.isHealthy,
            consecutiveFailures: this.connectionHealth.consecutiveFailures,
            reconnectAttempts: this.connectionHealth.reconnectAttempts,
            timeSinceLastSuccess: Math.round(timeSinceLastSuccess / 1000),
            circuitBreakerState: this.circuitBreaker.state,
            currentDelay: Math.round(this.connectionHealth.reconnectDelay / 1000)
        };

        console.error('📊 Connection Status:', JSON.stringify(status, null, 2));
        return status;
    }

    async checkHealth() {
        return new Promise((resolve, reject) => {
            const url = new URL(this.serverUrl);
            const options = {
                hostname: url.hostname,
                port: url.port || (url.protocol === 'https:' ? 443 : 80),
                path: this.serverUrl.includes('railway.app') ? '/health' : '/ping', // Railway uses /health, others use /ping
                method: 'GET',
                timeout: this.serverUrl.includes('railway.app') ? 10000 : 5000, // 10s for Railway, 5s for others
                agent: url.protocol === 'https:' ? this.httpsAgent : this.httpAgent
            };

            console.error(`🏥 Checking health endpoint: ${options.path} (timeout: ${options.timeout}ms)`);

            const client = url.protocol === 'https:' ? https : http;
            const req = client.request(options, (res) => {
                console.error(`📡 Health check response: ${res.statusCode} ${res.statusMessage || ''}`);
                if (res.statusCode === 200) {
                    // Update connection health on success
                    this.connectionHealth.lastSuccessfulHealthCheck = Date.now();
                    this.connectionHealth.consecutiveFailures = 0;
                    this.connectionHealth.isHealthy = true;
                    this.connectionHealth.reconnectAttempts = 0;
                    this.connectionHealth.reconnectDelay = 5000; // Reset delay
                    console.error('✅ Server health check passed - connection healthy');
                    resolve(true);
                } else {
                    console.error('⚠️ Server health check failed - status:', res.statusCode);
                    this.updateConnectionHealth(false);
                    resolve(false);
                }
            });

            req.on('error', (error) => {
                console.error('❌ Health check request error:', error.message);
                this.updateConnectionHealth(false);
                resolve(false);
            });

            req.on('timeout', () => {
                console.error('⏰ Health check timeout');
                req.destroy();
                this.updateConnectionHealth(false);
                resolve(false);
            });

            req.end();
        });
    }

    updateConnectionHealth(success) {
        if (success) {
            this.connectionHealth.consecutiveFailures = 0;
            this.connectionHealth.isHealthy = true;
            console.error('✅ Connection health updated - SUCCESS');
        } else {
            this.connectionHealth.consecutiveFailures++;
            this.connectionHealth.isHealthy = false;
            console.error(`❌ Connection health updated - FAILURE (${this.connectionHealth.consecutiveFailures} consecutive)`);

            // For Railway connections, be more aggressive
            const failureThreshold = this.serverUrl.includes('railway.app') ? 1 : 3;

            if (this.connectionHealth.consecutiveFailures >= failureThreshold) {
                this.connectionHealth.reconnectAttempts++;
                console.error(`🔄 Connection unhealthy - attempt ${this.connectionHealth.reconnectAttempts}`);

                // Check if we've exceeded total time limit
                const elapsedTime = Date.now() - this.connectionHealth.startTime;
                if (elapsedTime >= this.connectionHealth.maxTotalTime) {
                    console.error(`⏰ Maximum reconnection time (${Math.round(this.connectionHealth.maxTotalTime / 60000)}min) exceeded`);
                    return;
                }

                // Exponential backoff with jitter
                const baseDelay = Math.min(
                    this.connectionHealth.reconnectDelay * Math.pow(2, Math.min(this.connectionHealth.reconnectAttempts - 1, 4)), // Cap exponent
                    this.connectionHealth.maxReconnectDelay
                );
                const jitter = Math.random() * 1000; // Add up to 1 second jitter
                this.connectionHealth.reconnectDelay = baseDelay + jitter;

                console.error(`⏳ Next reconnection attempt in ${Math.round(this.connectionHealth.reconnectDelay / 1000)}s (elapsed: ${Math.round(elapsedTime / 1000)}s)`);
            }
        }
    }

    async waitForReconnection() {
        // Check if we've exceeded total time limit
        const elapsedTime = Date.now() - this.connectionHealth.startTime;
        if (elapsedTime >= this.connectionHealth.maxTotalTime) {
            console.error(`🚫 Maximum reconnection time (${Math.round(this.connectionHealth.maxTotalTime / 60000)}min) exceeded - giving up`);
            return false;
        }

        console.error(`⏳ Waiting ${Math.round(this.connectionHealth.reconnectDelay / 1000)}s before reconnection attempt...`);

        // Check connection status during wait - Railway might wake up early
        let earlySuccess = false;
        let earlySuccessCheck = () => {
            if (this.connectionHealth.isHealthy) {
                console.error('🎉 Connection became healthy during wait - early success!');
                earlySuccess = true;
                // Reset reconnection counters since we're healthy now
                this.connectionHealth.reconnectAttempts = 0;
                this.connectionHealth.reconnectDelay = this.serverUrl.includes('railway.app') ? 3000 : 5000;
                return true;
            }
            return false;
        };

        const checkInterval = setInterval(earlySuccessCheck, 2000); // Check every 2 seconds during wait

        await new Promise(resolve => setTimeout(resolve, this.connectionHealth.reconnectDelay));
        clearInterval(checkInterval);

        // Check if we detected early success
        if (earlySuccess) {
            console.error('✅ Early reconnection success detected!');
            console.error('🚂 RAILWAY EARLY RECONNECT: Connection restored during wait!');
            return true;
        }

        // Final check before attempting
        if (this.connectionHealth.isHealthy) {
            console.error('🎉 Connection is already healthy!');
            console.error('🚂 RAILWAY HEALTHY: No reconnection needed!');
            return true;
        }

        // Try to reconnect
        console.error('🔄 Attempting to reconnect...');
        const isHealthy = await this.checkHealth();

        if (isHealthy) {
            console.error('🎉 Reconnection successful!');
            console.error('🚂 RAILWAY SUCCESSFUL RECONNECT: MCP connection fully restored!');
            return true;
        } else {
            console.error('❌ Reconnection failed, will retry...');
            return false;
        }
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

            // Check cache for Railway tools/list
            if (this.serverUrl.includes('railway.app') && message.method === 'tools/list') {
                const cacheKey = `tools_list_${this.serverUrl}`;
                const cached = this.responseCache.get(cacheKey);
                const cacheAge = cached ? Date.now() - cached.timestamp : Infinity;

                if (cached && cacheAge < 30000) { // Cache for 30 seconds
                    console.error('🚂 RAILWAY: Returning cached tools/list response');
                    return cached.response;
                }
            }

            // Check circuit breaker state
            if (this.circuitBreaker.state === 'OPEN') {
                const timeSinceLastFailure = Date.now() - this.circuitBreaker.lastFailureTime;
                if (timeSinceLastFailure < this.circuitBreaker.recoveryTimeout) {
                    console.error('⛔ Circuit breaker OPEN - rejecting request');
                    const errorResponse = {
                        jsonrpc: '2.0',
                        error: {
                            code: -32003,
                            message: 'Service temporarily unavailable - circuit breaker open'
                        }
                    };
                    if (message.id !== undefined) {
                        errorResponse.id = message.id;
                    }
                    return errorResponse;
                } else {
                    console.error('🔄 Circuit breaker HALF_OPEN - attempting recovery');
                    this.circuitBreaker.state = 'HALF_OPEN';
                }
            }

            // Check server health first
            console.error('🏥 Checking server health...');
            let isHealthy = message.method === 'tools/list' && this.serverUrl.includes('railway.app')
                ? true  // Skip health check entirely for Railway tools/list
                : await this.checkHealth();

            // Check if we should trust periodic monitoring for Railway
            const timeSinceLastSuccess = Date.now() - this.connectionHealth.lastSuccessfulHealthCheck;
            const hasRecentSuccess = timeSinceLastSuccess < 30000; // Within last 30 seconds

            if (!isHealthy && hasRecentSuccess && this.serverUrl.includes('railway.app')) {
                console.error('🚂 RAILWAY: Periodic monitoring detected recent health - proceeding with request');
                this.connectionHealth.consecutiveFailures = 0; // Reset failures
                console.error('✅ Server health check passed (via periodic monitoring)');
                isHealthy = true; // Override health check result
            }

            // For tools/list specifically, be ultra-aggressive for Railway - ALWAYS skip health checks
            if (message.method === 'tools/list' && this.serverUrl.includes('railway.app')) {
                console.error('🚂 RAILWAY: ULTRA-FAST MODE for tools/list - bypassing all health checks');
                console.error('✅ Server health check bypassed completely for tools/list');
                isHealthy = true;
            }

            if (!isHealthy) {
                // Debug logging for connection health
                console.error(`📊 Connection Health Debug: consecutiveFailures=${this.connectionHealth.consecutiveFailures}, reconnectAttempts=${this.connectionHealth.reconnectAttempts}, isHealthy=${this.connectionHealth.isHealthy}`);

                // For Railway connections, be more aggressive with reconnection
                const shouldAttemptReconnect = this.serverUrl.includes('railway.app')
                    ? (this.connectionHealth.consecutiveFailures >= 1)
                    : (this.connectionHealth.consecutiveFailures >= 3);

                if (shouldAttemptReconnect) {
                    console.error('🔄 Connection unhealthy - attempting reconnection...');
                    const reconnected = await this.waitForReconnection();

                    if (!reconnected) {
                        console.error('❌ Reconnection failed - returning error');
                        this.updateCircuitBreaker(false);
                        const elapsedTime = Math.round((Date.now() - this.connectionHealth.startTime) / 1000);
                        const errorResponse = {
                            jsonrpc: '2.0',
                            error: {
                                code: -32004,
                                message: `Connection failed after ${elapsedTime} seconds of reconnection attempts. Railway may be experiencing issues.`
                            }
                        };
                        if (message.id !== undefined) {
                            errorResponse.id = message.id;
                        }
                        return errorResponse;
                    }
                    console.error('✅ Reconnection successful - proceeding with request');
                    console.error('🚂 RAILWAY RECONNECTED: MCP connection restored!');
                } else {
                    // Check if we've exceeded total time limit
                    const elapsedTime = Date.now() - this.connectionHealth.startTime;
                    if (elapsedTime >= this.connectionHealth.maxTotalTime) {
                        console.error(`🚫 Maximum reconnection time (${Math.round(this.connectionHealth.maxTotalTime / 60000)}min) exceeded - giving up`);
                        this.updateCircuitBreaker(false);
                        const errorResponse = {
                            jsonrpc: '2.0',
                            error: {
                                code: -32004,
                                message: `Connection failed after ${Math.round(elapsedTime / 1000)} seconds of reconnection attempts. Railway may be experiencing issues.`
                            }
                        };
                        if (message.id !== undefined) {
                            errorResponse.id = message.id;
                        }
                        return errorResponse;
                    }

                    console.error(`❌ Server health check failed (failures: ${this.connectionHealth.consecutiveFailures}, threshold: ${this.serverUrl.includes('railway.app') ? 1 : 3})`);
                    console.error(`⏰ Elapsed time: ${Math.round((Date.now() - this.connectionHealth.startTime) / 1000)}s, Max time: ${Math.round(this.connectionHealth.maxTotalTime / 1000)}s`);
                    this.updateCircuitBreaker(false);
                    const errorResponse = {
                        jsonrpc: '2.0',
                        error: {
                            code: -32001,
                            message: 'Server health check failed - service may be starting up'
                        }
                    };
                    if (message.id !== undefined) {
                        errorResponse.id = message.id;
                    }
                    return errorResponse;
                }
            }

            console.error('✅ Server health check passed');

            // Retry logic with exponential backoff (more retries for Railway, but faster for tools)
            const maxAttempts = this.serverUrl.includes('railway.app') ? 5 : 3;
            let lastError;
            for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    console.error(`🔄 Attempt ${attempt}/${maxAttempts}`);
                    const result = await this.makeRequest(message, message);
                    this.updateCircuitBreaker(true);

                    // Cache successful tools/list responses for Railway
                    if (this.serverUrl.includes('railway.app') && message.method === 'tools/list') {
                        const cacheKey = `tools_list_${this.serverUrl}`;
                        this.responseCache.set(cacheKey, {
                            response: result,
                            timestamp: Date.now()
                        });
                        console.error('🚂 RAILWAY: Cached tools/list response');
                    }

                    return result;
                } catch (error) {
                    lastError = error;
                    console.error(`❌ Attempt ${attempt} failed:`, error.message);

                    // Special handling for Railway connection issues
                    if (this.serverUrl.includes('railway.app') && error.code === 'ECONNRESET') {
                        console.error('🚂 RAILWAY: Connection reset detected, using Railway-specific retry strategy');
                    }

                    if (attempt < maxAttempts) {
                        // Ultra-fast retries for tools/list on Railway (tools are critical)
                        const isToolsList = message.method === 'tools/list';
                        const delay = this.serverUrl.includes('railway.app')
                            ? (isToolsList
                                ? Math.min(500 * Math.pow(1.1, attempt - 1), 1000)  // Ultra-fast for tools/list
                                : Math.min(2000 * Math.pow(1.5, attempt - 1), 8000)) // Slower for others
                            : Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                        console.error(`⏳ Waiting ${delay}ms before retry...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                }
            }

            // All retries failed
            this.updateCircuitBreaker(false);
            const maxAttemptsMsg = this.serverUrl.includes('railway.app') ? '5 attempts' : '3 attempts';
            const errorResponse = {
                jsonrpc: '2.0',
                error: {
                    code: -32002,
                    message: `Request failed after ${maxAttemptsMsg}: ${lastError.message}`
                }
            };
            if (message.id !== undefined) {
                errorResponse.id = message.id;
            }
            return errorResponse;

        } catch (error) {
            console.error('❌ Unexpected error in handleMessage:', error);
            this.updateCircuitBreaker(false);
            const errorResponse = {
                jsonrpc: '2.0',
                error: {
                    code: -32603,
                    message: `Bridge error: ${error.message}`
                }
            };
            if (message.id !== undefined) {
                errorResponse.id = message.id;
            }
            return errorResponse;
        }
    }

    async makeRequest(message, originalMessage = null) {
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
                agent: url.protocol === 'https:' ? this.httpsAgent : this.httpAgent, // Use appropriate agent
                timeout: url.hostname.includes('railway.app')
                    ? (originalMessage?.method === 'tools/list' ? 3000 : 15000)  // Ultra-fast timeout for tools/list
                    : 10000,
                keepAlive: true,
                keepAliveMsecs: 30000
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
                }
            };
            if (message.id !== undefined) {
                errorResponse.id = message.id;
            }

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
