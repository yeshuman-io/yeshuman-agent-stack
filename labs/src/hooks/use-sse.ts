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
 * @param threadCallbacks - Optional callbacks for thread-related delta events
 *
 * @returns Object with connection state, chat state, and actions
 *
 * Usage:
 * // Chat only (default)
 * const sse = useSSE(onMessageStart, token);
 *
 * // With persistent connection for real-time features
 * const sse = useSSE(onMessageStart, token, true);
 *
 * // With thread event callbacks
 * const sse = useSSE(onMessageStart, token, true, { onThreadCreated, onThreadUpdated, onMessageSaved });
 */
export const useSSE = (onMessageStart?: () => void, token?: string | null, autoConnect: boolean = false, threadCallbacks?: { onThreadCreated?: (data: any) => void; onThreadUpdated?: (data: any) => void; onThreadTitleGenerating?: (data: any) => void; onMessageSaved?: (data: any) => void; onUIEvent?: (data: any) => void }, currentThreadId?: string | null) => {
  // Core state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Thread management (received from parent)
  const effectiveCurrentThreadId = currentThreadId;

  // Token ref
  const tokenRef = useRef<string | null>(null);

  // Update token ref when token changes
  useEffect(() => {
    tokenRef.current = token || null;
  }, [token]);

  // Debug when currentThreadId changes
  useEffect(() => {
    console.log('🚨 [USE SSE] currentThreadId changed to:', currentThreadId, 'effectiveCurrentThreadId:', effectiveCurrentThreadId);
  }, [currentThreadId, effectiveCurrentThreadId]);

  // Content streaming state
  const [thinkingContent, setThinkingContent] = useState('');
  const [voiceLines, setVoiceLines] = useState<string[]>([]);
  const [memorySummaries, setMemorySummaries] = useState<string[]>([]);
  const [toolOutput, setToolOutput] = useState(''); // Keep for debugging
  const [activeTools, setActiveTools] = useState<string[]>([]);

  // SSE management
  const abortControllerRef = useRef<AbortController | null>(null);
  const contentBlocksRef = useRef<Record<number, ContentBlock>>({});
  const currentRunIdRef = useRef<string | null>(null);

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

        async onopen(response) {
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
              isUser: false,
              runId: currentRunIdRef.current || undefined
            }]);
          } else if (type === 'voice') {
            setVoiceLines(prev => [...prev, '']);
          } else if (type === 'memory') {
            setMemorySummaries(prev => [...prev, '']);
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

            case 'memory_delta':
              setMemorySummaries(prev => {
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

            case 'ui_delta':
              // Handle UI update events (e.g., profile changes, application updates)
              console.log('[SSE] 📡 RECEIVED ui_delta event:', delta);
              if (delta.ui_event) {
                console.log('[UI EVENT] 🎯 Processing UI event:', delta.ui_event);
                // Emit event for components to handle
                if (threadCallbacks?.onUIEvent) {
                  console.log('[UI EVENT] 🔄 Calling onUIEvent callback');
                  threadCallbacks.onUIEvent(delta.ui_event);
                } else {
                  console.warn('[UI EVENT] ⚠️ No onUIEvent callback registered');
                }
              } else {
                console.warn('[UI EVENT] ⚠️ ui_delta received but no ui_event data:', delta);
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
        if (data.thread_id && !effectiveCurrentThreadId) {
          console.log(`[THREAD] New thread created: ${data.thread_id}`);
          // Thread ID is managed by parent component, so we don't set it here
          console.log(`[THREAD] Thread ID received from backend: ${data.thread_id} (managed by parent)`);
        }

        // Trigger sarcastic animation on AI response
        if (onMessageStart) {
          console.log('🤖 AI response detected - triggering sarcastic animation');
          onMessageStart();
        }
        break;

      case 'run_id':
        console.log('🔗 Received runId event:', data);
        if (data.runId) {
          console.log('🔗 Setting runId from run_id event:', data.runId);
          currentRunIdRef.current = data.runId;

          // Patch runId onto the most recent AI message that doesn't have one
          setMessages(prev => {
            const next = [...prev];
            for (let i = next.length - 1; i >= 0; i--) {
              const m = next[i];
              if (!m.isUser && !m.runId) {
                console.log('🔗 Patching runId onto AI message:', { messageId: m.id, runId: data.runId });
                next[i] = { ...m, runId: data.runId };
                break;
              }
            }
            return next;
          });
        } else {
          console.log('⚠️ run_id event received but no runId:', data);
        }
        break;
        
      case 'message_stop':
        console.log('[MESSAGE STOP]');
        setIsLoading(false);
        break;


      case 'message_saved':
        console.log('🔄 [SSE THREAD] Message saved event received:', {
          thread_id: data.thread_id,
          message_id: data.message_id,
          message_type: data.message_type,
          content_length: data.content?.length || 0
        });
        // Emit thread event for UI updates
        if (threadCallbacks?.onMessageSaved) {
          console.log('🔄 [SSE THREAD] Calling onMessageSaved callback');
          threadCallbacks.onMessageSaved(data);
        } else {
          console.log('🔄 [SSE THREAD] No onMessageSaved callback registered');
        }
        break;

      default:
        console.log(`[SSE] Unhandled event: ${eventType}`);
    }
  }, []);

  // Send message function
  const sendMessage = useCallback(async (message: string, threadId?: string) => {
    console.log('🚀 [SEND MESSAGE] sendMessage function called with threadId:', threadId);
    console.log('🚨 [USE SSE] sendMessage called with:', {
      message: message.substring(0, 30) + (message.length > 30 ? '...' : ''),
      threadId: threadId,
      effectiveCurrentThreadId: effectiveCurrentThreadId,
      threadIdIsUndefined: threadId === undefined,
      threadIdIsNull: threadId === null,
      threadIdIsEmptyString: threadId === '',
      willUseCurrentThreadId: !threadId && effectiveCurrentThreadId,
      finalThreadId: threadId || effectiveCurrentThreadId,
      callStack: new Error().stack?.split('\n').slice(0, 5).join('\n')
    });
    console.log('🚨 [THREAD DEBUG] sendMessage() called with:', {
      message: message.substring(0, 30) + (message.length > 30 ? '...' : ''),
      threadId: threadId,
      threadIdType: typeof threadId,
      threadIdTruthy: !!threadId,
      effectiveCurrentThreadId: effectiveCurrentThreadId
    });
    if (!message.trim()) return;

    // Use current thread ID if none provided
    const finalThreadId = threadId || effectiveCurrentThreadId;
    console.log('🚨 [THREAD FIX] Using finalThreadId:', finalThreadId, 'original threadId:', threadId, 'effectiveCurrentThreadId:', effectiveCurrentThreadId);

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

      console.log('[SSE] Sending message:', {
        message: message.substring(0, 50) + (message.length > 50 ? '...' : ''),
        threadId,
        currentThreadId,
        final_thread_id: threadId || currentThreadId
      });

      await fetchEventSource(SSE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(tokenRef.current && { 'Authorization': `Bearer ${tokenRef.current}` }),
        },
        body: JSON.stringify({
          message,
          ...(finalThreadId && { thread_id: finalThreadId })
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
          console.log('[SSE] 🔄 RECEIVED RAW EVENT:', event.event, event.data?.substring(0, 200));
          if (!event.data?.trim()) return;

          try {
            const data = JSON.parse(event.data);
            console.log('[SSE] 📦 PARSED EVENT:', data);
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
    console.log('🚨 [THREAD DEBUG] startNewConversation() called!');
    // Clear local state - thread ID is managed by parent component
    setMessages([]);
    setThinkingContent('');
    setVoiceLines([]);
    setMemorySummaries([]);
    setActiveTools([]);
    console.log('[THREAD] Started new conversation (thread ID managed by parent)');
  }, []);

  return {
    // State
    messages,
    isConnected,
    isLoading,
    thinkingContent,
    voiceLines,
    memorySummaries,
    toolOutput,
    activeTools,
    currentThreadId,

    // Actions
    sendMessage,
    startNewConversation,
    setMessages
  };
};
