import { useState, useRef, useCallback } from 'react'
import { ThemeProvider } from './components/theme-provider'
import { Activity } from 'lucide-react'
import { AnimatedTitle } from './components/animated-title'
import { ModeToggle } from './components/mode-toggle'
import { ChatMessages, ChatInput } from './components/chat'
import { ThinkingPanel, VoicePanel, ToolsPanel, SystemPanel } from './components/panels'
import { SidebarProvider, SidebarInset, SidebarTrigger } from './components/ui/sidebar'
import { AppSidebar } from './components/app-sidebar'
import { useSSE } from './hooks/use-sse'
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
    sendMessage
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

  return (
    <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="flex flex-col">
          {/* Header */}
          <div className="border-b p-4 flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <SidebarTrigger />
              <AnimatedTitle onAnimationTrigger={(triggerFn) => {
                animationTriggerRef.current = triggerFn;
              }} />
            </div>
            <div className="flex items-center space-x-4">
              <Activity className={`h-4 w-4 ${isConnected ? 'text-green-500' : 'text-red-500'}`} />
              <ModeToggle />
            </div>
          </div>
          
          {/* Main Layout */}
          <div className="flex-1 flex">
            {/* Left: Chat */}
            <div className="w-1/2 border-r flex flex-col">
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
    </ThemeProvider>
  );
}

export default App;
