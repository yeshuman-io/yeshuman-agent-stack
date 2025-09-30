import React from 'react';
import { useSSE } from '../hooks/use-sse';
import { useAuth } from '../hooks/use-auth';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Wifi, WifiOff } from 'lucide-react';

/**
 * Example component showing how to use auto-connect for persistent SSE connections
 * This complements the existing chat system by establishing connections on page load
 */
export function AutoConnectExample() {
  const { token } = useAuth();

  // Enable auto-connect for persistent real-time connection
  const {
    isConnected,
    sendMessage,
    // Other chat functionality available when needed
  } = useSSE(undefined, token, true); // true = autoConnect

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Auto-Connect Example</span>
          <Badge variant={isConnected ? "default" : "secondary"}>
            {isConnected ? (
              <>
                <Wifi className="h-3 w-3 mr-1" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 mr-1" />
                Offline
              </>
            )}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm text-muted-foreground">
          <p><strong>Complementary Approach:</strong></p>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li>Extends existing <code>useSSE</code> hook with optional <code>autoConnect</code></li>
            <li>Same Activity icon in header shows connection status</li>
            <li>Persistent connection for future real-time features</li>
            <li>Seamlessly switches to chat mode when sending messages</li>
          </ul>
        </div>

        <div className="text-xs bg-blue-50 p-3 rounded">
          <p><strong>Future Ready:</strong> This connection can be extended to handle:</p>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li>Live profile updates from agent actions</li>
            <li>Real-time notifications</li>
            <li>System status updates</li>
            <li>Background processing feedback</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
