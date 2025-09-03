import { useState, useRef, useCallback } from 'react'
import { ThemeProvider } from './components/theme-provider'
import { Activity, RotateCcw } from 'lucide-react'
import { AnimatedTitle } from './components/animated-title'
import { ModeToggle } from './components/mode-toggle'
import { ChatMessages, ChatInput } from './components/chat'
import { ThinkingPanel, VoicePanel, ToolsPanel, SystemPanel } from './components/panels'
import { SidebarProvider, SidebarInset, SidebarTrigger } from './components/ui/sidebar'
import { AppSidebar } from './components/app-sidebar'
import { useSSE } from './hooks/use-sse'
import { AuthProvider } from './hooks/use-auth'
import './App.css'

function App() {
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
  });

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
    <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
      <AuthProvider>
        <SidebarProvider>
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
            {/* Left: Chat */}
            <div className="w-1/2 border-r flex flex-col min-h-0">
              <ChatMessages messages={messages} />
              <ChatInput 
                inputText={inputText}
                setInputText={setInputText}
                onSubmit={handleSubmit}
                isLoading={isLoading}
              />
            </div>
            
            {/* Right: 4-Panel Grid */}
            <div className="w-1/2 flex flex-col">
              {/* Top Row */}
              <div className="flex-1 flex">
                <ThinkingPanel content={thinkingContent} />
                <VoicePanel voiceLines={voiceLines} />
              </div>
              
              {/* Bottom Row */}
              <div className="flex-1 flex">
                <ToolsPanel activeTools={activeTools} />
                <SystemPanel systemLogs={systemLogs} />
              </div>
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
