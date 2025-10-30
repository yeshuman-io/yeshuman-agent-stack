import { useState, useRef, useCallback, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useSearchParams, useNavigate } from 'react-router-dom'
import { ThemeProvider } from './components/theme-provider'
import { Activity, RotateCcw } from 'lucide-react'
import { AnimatedTitle } from './components/animated-title'
import { ModeToggle } from './components/mode-toggle'
import { ChatMessages, ChatInput } from './components/chat'
import { MemoryPanel, VoicePanel, ToolsPanel, SystemPanel } from './components/panels'
import { SidebarProvider, SidebarInset, SidebarTrigger } from './components/ui/sidebar'
import { AppSidebar } from './components/app-sidebar'
import { Profile } from './components/profile'
import { LoginPage } from './components/login-page'
import { CandidateRoutes } from './components/routes/candidate-routes'
import { EmployerRoutes } from './components/routes/employer-routes'
import { RecruiterRoutes } from './components/routes/recruiter-routes'
import { AdministratorRoutes } from './components/routes/administrator-routes'
import { MemoriesPage } from './components/memories/memories-page'
import { useSSE } from './hooks/use-sse'
import { useAuth } from './hooks/use-auth'
import { useQueryClient } from '@tanstack/react-query'
import './App.css'

interface UserFocus {
  current_focus: string
  available_foci: string[]
  focus_confirmed: boolean
}

function AppContent() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Get auth state
  const { isAuthenticated, token } = useAuth();
  // Get query client for invalidation
  const queryClient = useQueryClient();

  // Input state (separate from SSE hook)
  const [inputText, setInputText] = useState('');
  const [systemLogs] = useState<string[]>([]);

  // Thread state
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(
    searchParams.get('thread') || null
  );

  // Focus state
  const [userFocus, setUserFocus] = useState<UserFocus | null>(null);

  // Animation trigger
  const animationTriggerRef = useRef<(() => void) | null>(null);

  // Load thread messages from API
  const loadThreadMessages = useCallback(async (threadId: string) => {
    try {
      console.log('📂 [THREAD NAVIGATION] Loading thread messages:', {
        threadId,
        tokenPresent: !!token,
        tokenPreview: token ? `${token.substring(0, 20)}...` : 'NO TOKEN'
      });
      setMessages([]); // Clear current messages

      const apiUrl = `/api/threads/${threadId}/messages`;
      console.log('📂 [THREAD NAVIGATION] Making request to:', apiUrl);

      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      console.log('📂 [THREAD NAVIGATION] Response received:', {
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries())
      });

      if (response.ok) {
        const threadMessages = await response.json();
        console.log('📂 [THREAD NAVIGATION] Raw API response:', threadMessages);
        console.log('📂 [THREAD NAVIGATION] Loaded thread messages successfully:', {
          threadId,
          messageCount: threadMessages.length,
          messages: threadMessages
        });

        // Convert API messages to ChatMessage format
        const chatMessages = threadMessages.map((msg: any, index: number) => {
          console.log(`📂 [THREAD NAVIGATION] Converting message ${index}:`, msg);
          const converted = {
            id: msg.id || `msg-${Date.now()}-${index}`,
            content: msg.text || msg.content || '',
            isUser: msg.message_type === 'human' || msg.role === 'user',
            runId: msg.run_id || undefined  // Include run_id for feedback buttons
          };
          console.log(`📂 [THREAD NAVIGATION] Converted to:`, converted);
          return converted;
        });

        console.log('📂 [THREAD NAVIGATION] Final chat messages:', chatMessages);
        setMessages(chatMessages);
        return true; // Success
      } else {
        const errorText = await response.text();
        console.error('📂 [THREAD NAVIGATION] Failed to load thread messages:', {
          threadId,
          status: response.status,
          statusText: response.statusText,
          errorBody: errorText
        });
        setMessages([]);
        return false; // Failed to load
      }
    } catch (error) {
      console.error('📂 [THREAD NAVIGATION] Error loading thread messages:', {
        threadId,
        error: error instanceof Error ? error.message : String(error)
      });
      setMessages([]);
      return false; // Failed to load
    }
  }, [token]);

  // Thread event callbacks - now simplified since most thread events come as UI deltas
  const threadCallbacks = {
    onUIEvent: (data: any) => {
      console.log('🔄 [UI EVENT] Received UI update event:', data);
      if (data.action === 'navigate' && data.target) {
        console.log(`🔄 [UI EVENT] Navigating to: ${data.target}`);
        navigate(data.target);
        // Also invalidate cache when navigating to profile - field highlighting handled by TanStack comparison
        if (data.target === '/profile') {
          console.log('🔄 [UI EVENT] Invalidating profile cache after navigation');
          queryClient.invalidateQueries({ queryKey: ['profile'] });
        }
      } else if (data.entity === 'profile' && data.action === 'updated') {
        console.log('🔄 [UI EVENT] Invalidating profile cache for real-time updates');
        queryClient.invalidateQueries({ queryKey: ['profile'] });
      } else if (data.entity === 'thread' && data.action === 'created') {
        console.log('🆕 [UI EVENT] Thread created:', data.entity_id);
        // Update current thread ID if we don't have one (for new conversations)
        if (!currentThreadId && data.entity_id) {
          console.log('🆕 [UI EVENT] Setting currentThreadId to newly created thread:', data.entity_id);
          setCurrentThreadId(data.entity_id);
          // Also update URL to reflect the new thread
          setSearchParams({ thread: data.entity_id });
        }
        queryClient.invalidateQueries({ queryKey: ['threads'] });
      } else if (data.entity === 'thread' && data.action === 'updated') {
        console.log('🔄 [UI EVENT] Thread updated:', data.entity_id);
        queryClient.invalidateQueries({ queryKey: ['threads'] });
      } else if (data.entity === 'thread' && data.action === 'title_updated') {
        console.log('🎯 [UI EVENT] Thread title updated:', data.entity_id, data.subject);
        queryClient.invalidateQueries({ queryKey: ['threads'] });
      } else if (data.entity === 'memory' && ['stored', 'retrieved'].includes(data.action)) {
        console.log('🧠 [UI EVENT] Memory event:', data.action, 'invalidating memories cache');
        queryClient.invalidateQueries({ queryKey: ['memories'] });
      } else {
        console.log(`🔄 [UI EVENT] Unhandled event: ${data.entity}.${data.action}`);
      }
    },
    onThreadTitleGenerating: (data: any) => {
      console.log('🎯 [APP] Thread title generating:', data);
      // Additional app-level handling if needed
    }
  };

  // Use SSE hook for all streaming functionality
  const {
    messages,
    isConnected,
    isLoading,
    thinkingContent,
    voiceLines,
    memorySummaries,
    activeTools,
    sendMessage,
    startNewConversation,
    setMessages
  } = useSSE(() => {
    // Trigger animation when AI response starts
    if (animationTriggerRef.current) {
      animationTriggerRef.current();
    }
  }, token, true, threadCallbacks, currentThreadId); // Auto-connect with thread event callbacks and current thread

  // Sync URL params with thread state
  useEffect(() => {
    const urlThreadId = searchParams.get('thread');
    console.log('🔗 [URL SYNC] useEffect triggered - Checking URL thread sync:', {
      urlThreadId,
      currentThreadId,
      urlHasThread: !!urlThreadId,
      currentThreadExists: !!currentThreadId,
      useEffectTriggered: true,
      timestamp: Date.now(),
      searchParamsString: searchParams.toString(),
      allSearchParams: Object.fromEntries(searchParams.entries())
    });

    const handleUrlThreadSync = async () => {
      if (urlThreadId) {
        // Always try to load thread messages when there's a thread ID in the URL
        // This handles both new URLs and page refreshes
        console.log('🔗 [URL SYNC] Thread ID found in URL - attempting to load:', {
          urlThreadId,
          currentThreadId,
          isPageRefresh: urlThreadId === currentThreadId
        });

        if (urlThreadId !== currentThreadId) {
          // URL changed - update our state first
          console.log('🔗 [URL SYNC] URL thread changed - updating state');
          setCurrentThreadId(urlThreadId);
        }

        // Always try to load messages for the thread in the URL
        console.log('🔗 [URL SYNC] About to call loadThreadMessages with:', urlThreadId);
        const loadSuccess = await loadThreadMessages(urlThreadId);

        if (!loadSuccess) {
          console.log('🔗 [URL SYNC] Failed to load thread from URL - clearing invalid thread ID');
          // Clear the invalid thread ID from URL
          const newSearchParams = new URLSearchParams(searchParams);
          newSearchParams.delete('thread');
          setSearchParams(newSearchParams);
          setCurrentThreadId(null);
          // Start new conversation
          startNewConversation();
        }
      } else if (!currentThreadId) {
        console.log('🔗 [URL SYNC] No thread in URL and no current thread - starting new conversation');
        console.log('🚨 [THREAD DEBUG] Calling startNewConversation()');
        startNewConversation();
      } else {
        console.log('🔗 [URL SYNC] No thread in URL but we have a current thread - keeping current state');
      }
    };

    handleUrlThreadSync();
  }, [searchParams, loadThreadMessages, startNewConversation, setSearchParams]);

  // Handle focus changes from sidebar
  const handleFocusChange = useCallback((focusData: UserFocus | null) => {
    console.log('🎯 [FOCUS CHANGE] Focus updated from sidebar:', focusData);
    setUserFocus(focusData);
  }, []);

  // Handle input submission
  const handleSubmit = useCallback(() => {
    console.log('🚨 [HANDLE SUBMIT] handleSubmit called with inputText:', inputText);
    if (inputText.trim()) {
      console.log('💬 [MESSAGE LIFECYCLE] Sending message:', {
        message: inputText.substring(0, 100) + (inputText.length > 100 ? '...' : ''),
        currentThreadId: currentThreadId,
        hasExistingThread: !!currentThreadId,
        willLetBackendCreateThread: !currentThreadId
      });

      // Let the backend create thread IDs - don't generate them in frontend
      // Pass null/undefined for new threads, existing thread_id for continuation
      console.log('🚨 [THREAD DEBUG] About to call sendMessage with:', {
        message: inputText.substring(0, 20),
        threadId: currentThreadId,  // null for new threads, existing ID for continuation
        threadIdType: typeof currentThreadId,
        threadIdTruthy: !!currentThreadId
      });
      sendMessage(inputText, currentThreadId || undefined);
      setInputText('');
    }
  }, [inputText, sendMessage, currentThreadId]);

  // Handle starting a new conversation (clears thread state)
  const handleNewConversation = useCallback(() => {
    console.log('🆕 [NEW CONVERSATION] Starting new conversation - clearing all thread state');

    // Clear thread state in parent component
    setCurrentThreadId(null);

    // Clear URL thread parameter
    const newSearchParams = new URLSearchParams(searchParams);
    newSearchParams.delete('thread');
    setSearchParams(newSearchParams);

    // Clear local state in use-sse hook
    startNewConversation();
  }, [searchParams, setSearchParams, startNewConversation]);

  // Handle starting conversation from dashboard
  const handleStartConversation = useCallback((message: string) => {
    console.log('🎯 [DASHBOARD CONVERSATION] Starting conversation from dashboard:', {
      message: message.substring(0, 100) + (message.length > 100 ? '...' : ''),
      currentThreadId
    });
    setInputText(message);
    // Small delay to ensure input is set before submitting
    setTimeout(() => {
      sendMessage(message, currentThreadId || undefined);
      setInputText('');
    }, 100);
  }, [sendMessage]);

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

  // Handle feedback submission
  const handleFeedback = useCallback(async (runId: string, score?: number, tags?: string[], comment?: string) => {
    console.log('👍 [FEEDBACK] Submitting feedback:', { runId, score, tags_count: tags?.length, comment_len: comment?.length });
    
    try {
      const response = await fetch('/api/feedback/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ run_id: runId, score, tags, comment })
      });
      
      const result = await response.json();
      console.log('👍 [FEEDBACK] Response:', { success: result.success, message: result.message, error: result.error });
      
      if (result.success) {
        console.log('✅ [FEEDBACK] Submitted successfully');
        // Show success toast (optional - could add react-hot-toast)
      } else {
        console.error('❌ [FEEDBACK] Failed:', result.error);
        // Show error toast (optional)
      }
    } catch (error) {
      console.error('❌ [FEEDBACK] Request failed:', error);
    }
  }, [token]);

  // If not authenticated, only show login page
  if (!isAuthenticated) {
    return (
      <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
      <SidebarProvider defaultOpen={false}>
          <AppSidebar
            onThreadSelect={handleThreadSelect}
            currentThreadId={currentThreadId}
            onClearCurrentThread={handleClearCurrentThread}
            onFocusChange={handleFocusChange}
            threadCallbacks={threadCallbacks}
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
                onClick={handleNewConversation}
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
              <ChatMessages messages={messages} onFeedback={handleFeedback} />
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
              <Route path="/memories" element={<MemoriesPage />} />

              {/* Focus-specific nested routes */}
              <Route path="/candidate/*" element={
                userFocus && userFocus.available_foci.includes('candidate') ? (
                  <CandidateRoutes onStartConversation={handleStartConversation} />
                ) : (
                  <Navigate to={`/${userFocus?.current_focus || 'candidate'}`} replace />
                )
              } />

              <Route path="/employer/*" element={
                userFocus && userFocus.available_foci.includes('employer') ? (
                  <EmployerRoutes onStartConversation={handleStartConversation} />
                ) : (
                  <Navigate to={`/${userFocus?.current_focus || 'candidate'}`} replace />
                )
              } />

              <Route path="/recruiter/*" element={
                userFocus && userFocus.available_foci.includes('recruiter') ? (
                  <RecruiterRoutes onStartConversation={handleStartConversation} />
                ) : (
                  <Navigate to={`/${userFocus?.current_focus || 'candidate'}`} replace />
                )
              } />

              <Route path="/administrator/*" element={
                userFocus && userFocus.available_foci.includes('administrator') ? (
                  <AdministratorRoutes onStartConversation={handleStartConversation} />
                ) : (
                  <Navigate to={`/${userFocus?.current_focus || 'candidate'}`} replace />
                )
              } />

              {/* Root redirect to current focus */}
              <Route path="/" element={
                userFocus ? (
                  <Navigate to={`/${userFocus.current_focus}`} replace />
                ) : (
                  <Navigate to="/candidate" replace />
                )
              } />

              {/* Catch-all redirect */}
              <Route path="*" element={<Navigate to={`/${userFocus?.current_focus || 'candidate'}`} replace />} />
            </Routes>
            </div>

            {/* Panels: 1/8 width, single column with equal height distribution */}
            <div className="flex-none w-1/8 flex flex-col h-full">
              <MemoryPanel memorySummaries={memorySummaries} />
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
