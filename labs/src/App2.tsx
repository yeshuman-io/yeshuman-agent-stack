import { useState, useRef, useCallback } from 'react'
import { ThemeProvider, useTheme } from './components/theme-provider'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { Button } from './components/ui/button'
import { Moon, Sun, Monitor, Bot, User, Wifi, Brain, Volume2, Wrench, Terminal, Cloud, Calculator } from 'lucide-react'
import './App.css'

// Core types for SSE events
interface ContentBlock {
  type: string;
  id: string;
  content: string;
}

interface SSEEvent {
  event: string;
  data: any;
}

interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
}

// Mode toggle component
const ModeToggle = () => {
  const { theme, setTheme } = useTheme();
  
  const nextTheme = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light';
  const titles = {
    light: 'Switch to dark mode',
    dark: 'Switch to system mode', 
    system: 'Switch to light mode'
  };
  
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(nextTheme)}
      className="h-8 w-8"
      title={titles[theme]}
    >
      {theme === 'light' && <Sun className="h-4 w-4" />}
      {theme === 'dark' && <Moon className="h-4 w-4" />}
      {theme === 'system' && <Monitor className="h-4 w-4" />}
      <span className="sr-only">
        Current: {theme} mode. Click to switch to {nextTheme} mode.
      </span>
    </Button>
  );
};

// Helper function to get icon for tool type
const getToolIcon = (toolName: string) => {
  switch (toolName.toLowerCase()) {
    case 'weather':
      return <Cloud className="h-4 w-4 text-muted-foreground" />;
    case 'calculator':
      return <Calculator className="h-4 w-4 text-muted-foreground" />;
    default:
      return <Wrench className="h-4 w-4 text-muted-foreground" />;
  }
};

function App2() {
  // Core state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  
  // Content streaming state
  const [thinkingContent, setThinkingContent] = useState('');
  const [voiceLines, setVoiceLines] = useState<string[]>([]);
  const [toolOutput, setToolOutput] = useState(''); // Keep for debugging
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [systemLogs] = useState<string[]>([]);
  
  // SSE management
  const abortControllerRef = useRef<AbortController | null>(null);
  const contentBlocksRef = useRef<Record<number, ContentBlock>>({});

  // Utility functions
  const generateId = (): string => {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
  };

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
        break;
        
      case 'message_stop':
        console.log('[MESSAGE STOP]');
        break;
        
      default:
        console.log(`[SSE] Unhandled event: ${eventType}`);
    }
  }, []);

  // Send message function
  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;
    
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
      setIsConnected(true);
      
      await fetchEventSource('http://localhost:8000/agent/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ message }),
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
        },
        
        onerror(error) {
          console.error('[SSE] Error:', error);
          setIsConnected(false);
        }
      });
      
    } catch (error) {
      console.error('[SEND] Error:', error);
      setIsConnected(false);
    }
  }, [handleSSEEvent]);

  // Handle input submission
  const handleSubmit = useCallback(() => {
    if (inputText.trim()) {
      sendMessage(inputText);
      setInputText('');
    }
  }, [inputText, sendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <ThemeProvider defaultTheme="dark" storageKey="yeshuman-v2-theme">
      <div className="h-screen flex flex-col bg-background">
        {/* Header */}
        <div className="border-b p-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-semibold">YesHuman</h1>
          </div>
          <div className="flex items-center space-x-4">
            <Wifi className={`h-4 w-4 ${isConnected ? 'text-green-500' : 'text-red-500'}`} />
            <ModeToggle />
          </div>
        </div>
        
        {/* Main Layout */}
        <div className="flex-1 flex">
          {/* Left: Chat */}
          <div className="w-1/2 border-r flex flex-col">
            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-4">
                {messages.map(message => (
                  <div key={message.id} className={`flex gap-3 ${message.isUser ? 'flex-row-reverse' : ''}`}>
                    <div className="w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground">
                      {message.isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </div>
                    <div className="flex-1 bg-muted/50 rounded-lg p-3">
                      <div className="whitespace-pre-wrap text-sm">
                        {message.content}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Input Area */}
            <div className="border-t p-4">
              <div className="flex gap-2">
                <textarea
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your message... (Ctrl+Enter to send)"
                  className="flex-1 resize-none border rounded-md p-2 min-h-[60px] text-sm bg-background"
                  rows={2}
                />
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim()}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
          
          {/* Right: 4-Panel Grid */}
          <div className="w-1/2 flex flex-col">
            {/* Top Row */}
            <div className="flex-1 flex">
              {/* Thinking Panel */}
              <div className="w-1/2 border-r border-b p-4">
                <div className="flex items-center mb-2">
                  <Brain className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-xs text-muted-foreground/70 whitespace-pre-wrap font-mono">
                  {thinkingContent}
                </div>
              </div>
              
              {/* Voice Panel */}
              <div className="w-1/2 border-b p-4">
                <div className="flex items-center mb-2">
                  <Volume2 className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="space-y-1">
                  {voiceLines.map((line, i) => (
                    <div key={i} className="text-xs text-muted-foreground/70 italic">
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            {/* Bottom Row */}
            <div className="flex-1 flex">
              {/* Tools Panel */}
              <div className="w-1/2 border-r p-4">
                <div className="flex items-center mb-2">
                  <Wrench className="h-4 w-4 text-muted-foreground" />
                </div>
                {/* Display active tools as icons */}
                <div className="flex flex-wrap gap-2">
                  {activeTools.map((tool, index) => (
                    <div key={index} className="flex items-center space-x-1">
                      {getToolIcon(tool)}
                    </div>
                  ))}
                  {activeTools.length === 0 && (
                    <div className="text-xs text-muted-foreground/50 italic">No active tools</div>
                  )}
                </div>
              </div>
              
              {/* System Panel */}
              <div className="w-1/2 p-4">
                <div className="flex items-center mb-2">
                  <Terminal className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="space-y-1">
                  {systemLogs.map((log, i) => (
                    <div key={i} className="text-xs text-muted-foreground/70">
                      {log}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ThemeProvider>
  );
}

export default App2;
