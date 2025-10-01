import { useState, useRef, useCallback, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useSearchParams } from 'react-router-dom'
import { ThemeProvider } from './components/theme-provider'
import { Activity, RotateCcw } from 'lucide-react'
import { AnimatedTitle } from './components/animated-title'
import { ModeToggle } from './components/mode-toggle'
import { ChatMessages, ChatInput } from './components/chat'
import { ThinkingPanel, VoicePanel, ToolsPanel, SystemPanel } from './components/panels'
import { SidebarProvider, SidebarInset, SidebarTrigger } from './components/ui/sidebar'
import { AppSidebar } from './components/app-sidebar'
import { Profile } from './components/profile'
import { useSSE } from './hooks/use-sse'
import { useAuth } from './hooks/use-auth'
import { useQueryClient } from '@tanstack/react-query'
import './App.css'

function AppContent() {
  const [searchParams, setSearchParams] = useSearchParams();
  // Get auth token
  const { token } = useAuth();
  // Get query client for invalidation
  const queryClient = useQueryClient();

  // Input state (separate from SSE hook)
  const [inputText, setInputText] = useState('');
  const [systemLogs] = useState<string[]>([]);

  // Thread state
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(
    searchParams.get('thread') || null
  );

  // Animation trigger
  const animationTriggerRef = useRef<(() => void) | null>(null);

  // Load thread messages from API
  const loadThreadMessages = useCallback(async (threadId: string) => {
    try {
      console.log('📂 [THREAD NAVIGATION] Loading thread messages:', {
        threadId,
        tokenPresent: !!token
      });
      setMessages([]); // Clear current messages

      const response = await fetch(`/api/threads/${threadId}/messages`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const threadMessages = await response.json();
        console.log('📂 [THREAD NAVIGATION] Loaded thread messages successfully:', {
          threadId,
          messageCount: threadMessages.length,
          messageTypes: threadMessages.map((msg: any) => msg.message_type)
        });

        // Convert API messages to ChatMessage format
        const chatMessages = threadMessages.map((msg: any) => ({
          id: msg.id || `msg-${Date.now()}`,
          content: msg.text || msg.content || '',
          isUser: msg.message_type === 'human' || msg.role === 'user'
        }));

        setMessages(chatMessages);
      } else {
        console.error('📂 [THREAD NAVIGATION] Failed to load thread messages:', {
          threadId,
          status: response.status,
          statusText: response.statusText
        });
        setMessages([]);
      }
    } catch (error) {
      console.error('📂 [THREAD NAVIGATION] Error loading thread messages:', {
        threadId,
        error: error instanceof Error ? error.message : String(error)
      });
      setMessages([]);
    }
  }, [token]);

  // Thread event callbacks for TanStack Query invalidation
  const threadCallbacks = {
    onThreadCreated: (data: any) => {
      console.log('🔄 [THREAD DELTA] Thread created:', {
        thread_id: data.thread_id,
        subject: data.subject,
        user_id: data.user_id,
        is_anonymous: data.is_anonymous,
        created_at: data.created_at
      });
      console.log('🔄 [THREAD DELTA] Invalidating threads query for sidebar refresh');
      queryClient.invalidateQueries({ queryKey: ['threads'] });
      // Update URL if it's a new thread and we don't have one
      if (!currentThreadId) {
        console.log('🔄 [THREAD DELTA] Setting URL to new thread:', data.thread_id);
        setSearchParams({ thread: data.thread_id });
      }
    },
    onThreadUpdated: (data: any) => {
      console.log('🔄 [THREAD DELTA] Thread updated:', {
        thread_id: data.thread_id,
        message_count: data.message_count,
        updated_at: data.updated_at
      });
      console.log('🔄 [THREAD DELTA] Invalidating threads query for sidebar refresh');
      queryClient.invalidateQueries({ queryKey: ['threads'] });
    },
    onMessageSaved: (data: any) => {
      console.log('🔄 [THREAD DELTA] Message saved:', {
        thread_id: data.thread_id,
        message_id: data.message_id,
        message_type: data.message_type,
        content_preview: data.content?.substring(0, 50) + (data.content?.length > 50 ? '...' : '')
      });
      console.log('🔄 [THREAD DELTA] Invalidating thread messages cache');
      queryClient.invalidateQueries({ queryKey: ['thread', data.thread_id] });
    }
  };

  // Use SSE hook for all streaming functionality
  const {
    messages,
    isConnected,
    isLoading,
    thinkingContent,
    voiceLines,
    activeTools,
    sendMessage,
    startNewConversation,
    setMessages
  } = useSSE(() => {
    // Trigger animation when AI response starts
    if (animationTriggerRef.current) {
      animationTriggerRef.current();
    }
  }, token, true, threadCallbacks); // Auto-connect with thread event callbacks

  // Sync URL params with thread state
  useEffect(() => {
    const urlThreadId = searchParams.get('thread');
    console.log('🔗 [URL SYNC] Checking URL thread sync:', {
      urlThreadId,
      currentThreadId,
      needsSync: urlThreadId !== currentThreadId
    });

    if (urlThreadId !== currentThreadId) {
      if (urlThreadId) {
        console.log('🔗 [URL SYNC] Setting current thread from URL:', {
          newThreadId: urlThreadId,
          previousThreadId: currentThreadId
        });
        setCurrentThreadId(urlThreadId);
        // Load thread messages when URL changes
        loadThreadMessages(urlThreadId);
      } else {
        console.log('🔗 [URL SYNC] Clearing thread (new conversation):', {
          previousThreadId: currentThreadId
        });
        setCurrentThreadId(null);
        setMessages([]); // Clear messages for new conversation
      }
    }
  }, [searchParams, loadThreadMessages]);

  // Handle input submission
  const handleSubmit = useCallback(() => {
    if (inputText.trim()) {
      console.log('💬 [MESSAGE LIFECYCLE] Sending message:', {
        message: inputText.substring(0, 100) + (inputText.length > 100 ? '...' : ''),
        currentThreadId: currentThreadId,
        hasExistingThread: !!currentThreadId
      });
      sendMessage(inputText);
      setInputText('');
    }
  }, [inputText, sendMessage, currentThreadId]);

  // Handle thread selection from sidebar
  const handleThreadSelect = useCallback((threadId: string) => {
    console.log('📂 [THREAD NAVIGATION] Thread selected from sidebar:', {
      selectedThreadId: threadId,
      previousThreadId: currentThreadId,
      switchingThreads: threadId !== currentThreadId
    });
    // Update URL params - the useEffect will handle loading messages
    setSearchParams({ thread: threadId });
  }, [setSearchParams, currentThreadId]);

  const handleClearCurrentThread = useCallback(() => {
    console.log('🗑️ [THREAD CLEAR] Clearing current thread view');
    setCurrentThreadId(null);
    setSearchParams({});
  }, [setSearchParams]);

  return (
    <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
      <SidebarProvider defaultOpen={false}>
          <AppSidebar
            onThreadSelect={handleThreadSelect}
            currentThreadId={currentThreadId}
            onClearCurrentThread={handleClearCurrentThread}
          />
          <SidebarInset className="flex flex-col h-screen">
          {/* Header */}
          <div className="border-b p-4 flex justify-between items-center flex-shrink-0">
            <div className="flex items-center space-x-2">
              <SidebarTrigger />
              <AnimatedTitle onAnimationTrigger={(triggerFn) => {
                animationTriggerRef.current = triggerFn;
              }} />
            </div>
            <div className="flex items-center space-x-4">
              <Activity className={`h-4 w-4 ${isConnected ? 'text-green-500' : 'text-red-500'}`} />
              <button
                onClick={startNewConversation}
                className="flex items-center space-x-2 px-3 py-1 bg-muted hover:bg-muted/80 rounded-md text-sm transition-colors"
                title="Start new conversation"
              >
                <RotateCcw className="h-4 w-4" />
                <span>New</span>
              </button>
              <ModeToggle />
            </div>
          </div>

          {/* Main Layout */}
          <div className="flex-1 flex min-h-0">
            {/* Chat: 1/4 width */}
            <div className="flex-none w-1/4 border-r flex flex-col min-h-0">
              <ChatMessages messages={messages} />
              <ChatInput
                inputText={inputText}
                setInputText={setInputText}
                onSubmit={handleSubmit}
                isLoading={isLoading}
              />
            </div>

            {/* Content Area: ~5/8 width (flex-1 makes it take remaining space) */}
            <div className="flex-1 border-r bg-background">
              <Routes>
                <Route path="/profile" element={<Profile />} />
                <Route path="/" element={
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center text-muted-foreground">
                      <p className="text-lg font-medium mb-2">Welcome to YesHuman</p>
                      <p className="text-sm">Start a conversation to begin your AI journey</p>
                    </div>
                  </div>
                } />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>

            {/* Panels: 1/8 width, single column with equal height distribution */}
            <div className="flex-none w-1/8 flex flex-col h-full">
              <ThinkingPanel content={thinkingContent} />
              <VoicePanel voiceLines={voiceLines} />
              <ToolsPanel activeTools={activeTools} />
              <SystemPanel systemLogs={systemLogs} />
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ThemeProvider>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
