import { useState, useRef, useCallback } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
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
import './App.css'

function App() {
  // Get auth token
  const { token } = useAuth();

  // Input state (separate from SSE hook)
  const [inputText, setInputText] = useState('');
  const [systemLogs] = useState<string[]>([]);

  // Animation trigger
  const animationTriggerRef = useRef<(() => void) | null>(null);

  // Use SSE hook for all streaming functionality
  const {
    messages,
    isConnected,
    isLoading,
    thinkingContent,
    voiceLines,
    activeTools,
    currentThreadId,
    sendMessage,
    startNewConversation,
    setMessages
  } = useSSE(() => {
    // Trigger animation when AI response starts
    if (animationTriggerRef.current) {
      animationTriggerRef.current();
    }
  }, token, true); // Auto-connect on load for persistent real-time connection

  // Handle input submission
  const handleSubmit = useCallback(() => {
    if (inputText.trim()) {
      sendMessage(inputText);
      setInputText('');
    }
  }, [inputText, sendMessage]);

  // Handle thread selection from sidebar
  const handleThreadSelect = useCallback(async (threadId: string) => {
    console.log('Loading thread:', threadId)

    try {
      // Clear current messages first
      setMessages([])

      // Fetch thread messages from API
      const response = await fetch(`/api/threads/${threadId}/messages`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const threadMessages = await response.json()
        console.log('Loaded thread messages:', threadMessages.length)

        // Convert API messages to ChatMessage format
        const chatMessages = threadMessages.map((msg: any) => ({
          id: msg.id || `msg-${Date.now()}`,
          content: msg.text || msg.content || '',
          isUser: msg.message_type === 'human' || msg.role === 'user'
        }))

        // Update messages state using the SSE hook's setMessages
        setMessages(chatMessages)
        console.log('Thread loaded with', chatMessages.length, 'messages')

      } else {
        console.error('Failed to load thread messages:', response.status, response.statusText)
        // Clear messages on error
        setMessages([])
      }

    } catch (error) {
      console.error('Error loading thread:', error)
      setMessages([])
    }
  }, []);

  return (
    <Router>
      <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
        <SidebarProvider defaultOpen={false}>
            <AppSidebar onThreadSelect={handleThreadSelect} />
            <SidebarInset className="flex flex-col h-screen">
            {/* Header */}
            <div className="border-b p-4 flex justify-between items-center flex-shrink-0">
              <div className="flex items-center space-x-2">
                <SidebarTrigger />
                <AnimatedTitle onAnimationTrigger={(triggerFn) => {
                  animationTriggerRef.current = triggerFn;
                }} />
                {currentThreadId && (
                  <div className="text-xs text-muted-foreground px-2 py-1 bg-muted rounded">
                    Thread: {currentThreadId.slice(-8)}
                  </div>
                )}
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
                        <div className="text-lg font-medium mb-2">Content Area</div>
                        <div className="text-sm">Profile, Opportunities, and other pages will appear here</div>
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
    </Router>
  );
}

export default App;
