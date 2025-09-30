import { useState, useRef, useCallback, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { SSE_ENDPOINT } from '../constants';
import type { ChatMessage, SSEEvent, ContentBlock } from '../types';

/**
 * useSSE Hook - Handles both chat messages and persistent real-time connections
 *
 * @param onMessageStart - Callback when AI starts responding (chat mode only)
 * @param token - JWT authentication token
 * @param autoConnect - If true, establishes persistent connection on mount for real-time features
 *
 * @returns Object with connection state, chat state, and actions
 *
 * Usage:
 * // Chat only (default)
 * const sse = useSSE(onMessageStart, token);
 *
 * // With persistent connection for real-time features
 * const sse = useSSE(onMessageStart, token, true);
 */
export const useSSE = (onMessageStart?: () => void, token?: string | null, autoConnect: boolean = false) => {
  // Core state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Thread management
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);

  // Token ref
  const tokenRef = useRef<string | null>(null);

  // Update token ref when token changes
  useEffect(() => {
    tokenRef.current = token || null;
  }, [token]);

  // Content streaming state
  const [thinkingContent, setThinkingContent] = useState('');
  const [voiceLines, setVoiceLines] = useState<string[]>([]);
  const [toolOutput, setToolOutput] = useState(''); // Keep for debugging
  const [activeTools, setActiveTools] = useState<string[]>([]);

  // SSE management
  const abortControllerRef = useRef<AbortController | null>(null);
  const contentBlocksRef = useRef<Record<number, ContentBlock>>({});

  // Utility function
  const generateId = (): string => {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
  };

  // Establish persistent connection for real-time features
  const establishPersistentConnection = useCallback(async () => {
    if (!tokenRef.current || isConnected) return;

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      console.log('[SSE] Establishing persistent connection...');

      await fetchEventSource(SSE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(tokenRef.current && { 'Authorization': `Bearer ${tokenRef.current}` }),
        },
        body: JSON.stringify({
          connect_only: true  // Special flag for persistent connections
        }),
        signal: abortController.signal,

        onopen(response) {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          console.log('[SSE] Persistent connection established');
          setIsConnected(true);
        },

        onmessage(event) {
          if (!event.data?.trim()) return;

          try {
            const data = JSON.parse(event.data);
            // Handle persistent connection events (heartbeats, etc.)
            if (data.type === 'heartbeat') {
              console.log('[SSE] Heartbeat received');
            } else if (data.type === 'connected') {
              console.log('[SSE] Persistent connection confirmed:', data);
            }
            // Future: handle profile updates, notifications, etc.
          } catch (error) {
            console.error('[SSE] Parse error in persistent connection:', error);
          }
        },

        onclose() {
          console.log('[SSE] Persistent connection closed');
          setIsConnected(false);
        },

        onerror(error) {
          console.error('[SSE] Persistent connection error:', error);
          setIsConnected(false);
        }
      });

    } catch (error) {
      console.error('[SSE] Failed to establish persistent connection:', error);
      setIsConnected(false);
    }
  }, [isConnected]);

  // Disconnect from current connection
  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      console.log('[SSE] Disconnecting...');
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && token && !isConnected) {
      establishPersistentConnection();
    }

    return () => {
      if (autoConnect && isConnected) {
        disconnect();
      }
    };
  }, [autoConnect, token, establishPersistentConnection, disconnect, isConnected]);

  // Core SSE event handler
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    const { event: eventType, data } = event;
    
    console.log(`[SSE] ${eventType}:`, data);
    
    switch (eventType) {
      case 'content_block_start':
        if (data.content_block) {
          const { index, content_block } = data;
          const { type, id } = content_block;
          
          // Store content block
          contentBlocksRef.current[index] = {
            id,
            type,
            content: ''
          };
          
          // Initialize UI based on content type
          if (type === 'text') {
            setMessages(prev => [...prev, {
              id,
              content: '',
              isUser: false
            }]);
          } else if (type === 'voice') {
            setVoiceLines(prev => [...prev, '']);
          }
          
          console.log(`[BLOCK START] ${type} block #${index} (${id})`);
        }
        break;
        
      case 'content_block_delta':
        if (data.delta && data.index !== undefined) {
          const { index, delta } = data;
          const { text } = delta;
          const block = contentBlocksRef.current[index];
      
          if (!block) {
            console.warn(`[DELTA] Unknown block #${index}`);
            return;
          }
      
          // Update stored content
          block.content += text || '';
          
          // Route to appropriate UI based on delta type
          switch (delta.type) {
            case 'message_delta':
              // Update main chat message
              setMessages(prev => prev.map(msg => 
                msg.id === block.id 
                  ? { ...msg, content: block.content }
                  : msg
              ));
              break;
              
            case 'thinking_delta':
              setThinkingContent(prev => prev + (text || ''));
              break;
              
            case 'voice_delta':
              setVoiceLines(prev => {
                if (prev.length === 0) return [text || ''];
                const copy = [...prev];
                copy[copy.length - 1] += text || '';
                return copy;
              });
              break;
              
            case 'tool_delta':
              // Parse tool content to extract tool names
              const content = (text || '');
              setToolOutput(prev => prev + content);

              // Extract tool names from content like "🔧 Calling tools: weather, weather, weather"
              const toolMatch = content.match(/Calling tools: (.+)/);
              if (toolMatch) {
                const toolNames = toolMatch[1].split(', ').map((name: string) => name.trim());
                setActiveTools(toolNames);
              }
              break;

            case 'tool_complete_delta':
              // Clear completed tools
              const completeContent = (text || '');
              setToolOutput(prev => prev + completeContent);

              // Extract completed tool names and remove them from active tools
              const completeMatch = completeContent.match(/Completed tools: (.+)/);
              if (completeMatch) {
                const completedToolNames = completeMatch[1].split(', ').map((name: string) => name.trim());
                setActiveTools(prev => prev.filter(tool => !completedToolNames.includes(tool)));
              }
              break;
              
            default:
              console.log(`[DELTA] Unknown type: ${delta.type}`);
          }
        }
        break;
        
      case 'content_block_stop':
        if (data.index !== undefined) {
          const block = contentBlocksRef.current[data.index];
          console.log(`[BLOCK STOP] ${block?.type} block #${data.index}`);
        }
        break;
        
      case 'message_start':
        // Clear previous content
        setThinkingContent('');
        setToolOutput('');
        console.log('[MESSAGE START]');

        // Extract thread_id if provided (for new threads)
        if (data.thread_id && !currentThreadId) {
          console.log(`[THREAD] New thread created: ${data.thread_id}`);
          setCurrentThreadId(data.thread_id);
        }

        // Trigger sarcastic animation on AI response
        if (onMessageStart) {
          console.log('🤖 AI response detected - triggering sarcastic animation');
          onMessageStart();
        }
        break;
        
      case 'message_stop':
        console.log('[MESSAGE STOP]');
        setIsLoading(false);
        break;

      case 'thread_created':
        console.log('[SSE] Thread created:', data);
        // Emit thread event for UI updates
        if (threadCallbacks?.onThreadCreated) {
          threadCallbacks.onThreadCreated(data);
        }
        break;

      case 'thread_updated':
        console.log('[SSE] Thread updated:', data);
        // Emit thread event for UI updates
        if (threadCallbacks?.onThreadUpdated) {
          threadCallbacks.onThreadUpdated(data);
        }
        break;

      case 'message_saved':
        console.log('[SSE] Message saved:', data);
        // Emit thread event for UI updates
        if (threadCallbacks?.onMessageSaved) {
          threadCallbacks.onMessageSaved(data);
        }
        break;

      default:
        console.log(`[SSE] Unhandled event: ${eventType}`);
    }
  }, []);

  // Send message function
  const sendMessage = useCallback(async (message: string, threadId?: string) => {
    if (!message.trim()) return;

    // If we're in persistent mode, disconnect first
    if (isConnected && autoConnect) {
      disconnect();
    }

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: generateId(),
      content: message,
      isUser: true
    };
    setMessages(prev => [...prev, userMessage]);

    // Clean up existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    // Clear content blocks and tools
    contentBlocksRef.current = {};
    setActiveTools([]);
    
    try {
      setIsLoading(true);
      setIsConnected(true);

      console.log('🚀 About to call fetchEventSource with URL:', SSE_ENDPOINT);
      console.log('🚀 SSE_ENDPOINT type:', typeof SSE_ENDPOINT);
      console.log('🚀 SSE_ENDPOINT length:', SSE_ENDPOINT.length);
      console.log('🚀 SSE_ENDPOINT chars:', SSE_ENDPOINT.split('').map(c => c.charCodeAt(0)));
      console.log('🚀 window.location.origin:', window.location.origin);
      console.log('🚀 document.baseURI:', document.baseURI);

      // Check if URL is malformed
      if (SSE_ENDPOINT.includes('=')) {
        console.error('🚨 MALFORMED URL DETECTED:', SSE_ENDPOINT);
        console.error('🚨 URL contains = character at position:', SSE_ENDPOINT.indexOf('='));
      }

      await fetchEventSource(SSE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(tokenRef.current && { 'Authorization': `Bearer ${tokenRef.current}` }),
        },
        body: JSON.stringify({
          message,
          ...((threadId || currentThreadId) && { thread_id: threadId || currentThreadId })
        }),
        signal: abortController.signal,
        
        onopen(response) {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          console.log('[SSE] Connection opened');
          return Promise.resolve();
        },
        
        onmessage(event) {
          if (!event.data?.trim()) return;
          
          try {
            const data = JSON.parse(event.data);
            handleSSEEvent({ event: event.event, data });
          } catch (error) {
            console.error('[SSE] Parse error:', error);
          }
        },
        
        onclose() {
          console.log('[SSE] Connection closed');
          setIsConnected(false);
          setIsLoading(false);
        },
        
        onerror(error) {
          console.error('[SSE] Error:', error);
          setIsConnected(false);
          setIsLoading(false);
        }
      });
      
    } catch (error) {
      console.error('[SEND] Error:', error);
      setIsConnected(false);
      setIsLoading(false);
    }
  }, [handleSSEEvent, autoConnect, isConnected, disconnect]);

  // Function to start a new conversation
  const startNewConversation = useCallback(() => {
    setCurrentThreadId(null);
    setMessages([]);
    setThinkingContent('');
    setVoiceLines([]);
    setActiveTools([]);
    console.log('[THREAD] Started new conversation');
  }, []);

  return {
    // State
    messages,
    isConnected,
    isLoading,
    thinkingContent,
    voiceLines,
    toolOutput,
    activeTools,
    currentThreadId,

    // Actions
    sendMessage,
    startNewConversation,
    setMessages
  };
};
