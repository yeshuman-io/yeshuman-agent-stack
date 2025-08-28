import { useState, useEffect, useRef, useCallback } from 'react'
import { ThemeProvider, useTheme } from './components/theme-provider'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from './components/ui/card'
import { ScrollArea } from './components/ui/scroll-area'
import { Input } from './components/ui/input'
import { Button } from './components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar'
import { Switch } from './components/ui/switch'
import { Label } from './components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs'
import { Textarea } from './components/ui/textarea'
import { Moon, Sun, AlertTriangle } from 'lucide-react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import './App.css'

// Define types for our messages and events
interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
}

interface StreamEvent {
  id: string;
  content: string;
  timestamp: Date;
}

interface SystemNotification {
  id: string;
  content: string;
  timestamp: Date;
  isError?: boolean;
}

// Anthropic SSE event interfaces
interface ContentBlock {
  type: string;
  id: string;
}

interface AnthropicDelta {
  type?: string;
  text?: string;
  stop_reason?: string;
  stop_sequence?: string | null;
}

interface AnthropicEvent {
  type: string;
  index?: number;
  message?: { content: any[] };
  content_block?: ContentBlock;
  delta?: AnthropicDelta;
  usage?: { output_tokens: number };
}

// Type for legacy event data
interface LegacyEventData {
  type?: string;
  content?: string;
  error?: { message: string };
}

// Mode toggle component
const ModeToggle = () => {
  const { theme, setTheme } = useTheme();
  
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
    >
      {theme === "light" ? (
        <Moon className="h-5 w-5" />
      ) : (
        <Sun className="h-5 w-5" />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
};

// Utility function to generate unique IDs
const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

// Chat input component moved outside the App component
interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  handleSendMessage: () => void;
  shortcutMode: boolean;
}

const ChatInput = ({ inputText, setInputText, handleSendMessage, shortcutMode }: ChatInputProps) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Enter to send in shortcut mode
    if (shortcutMode && e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSendMessage();
      return;
    }
    
    // Regular Enter or Shift+Enter for newline
    if (e.key === 'Enter' && !e.ctrlKey) {
      // Don't prevent default to allow newline
      return;
    }
  };

  return (
    <div className="flex gap-2 p-3 w-full">
      <Textarea 
        placeholder={shortcutMode ? "Type your message... (Ctrl+Enter to send)" : "Type your message..."}
        className="flex-1 min-h-[60px] resize-none"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      {!shortcutMode && (
        <Button onClick={handleSendMessage}>Send</Button>
      )}
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [voiceEvents, setVoiceEvents] = useState<StreamEvent[]>([]);
  const [thinkingEvents, setThinkingEvents] = useState<StreamEvent[]>([]);
  const [toolEvents, setToolEvents] = useState<StreamEvent[]>([]);
  const [knowledgeEvents, setKnowledgeEvents] = useState<StreamEvent[]>([]);
  const [conductorEvents, setConductorEvents] = useState<StreamEvent[]>([]);
  const [systemNotifications, setSystemNotifications] = useState<SystemNotification[]>([]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [shortcutMode, setShortcutMode] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const inputRef = useRef<HTMLInputElement>(null);
  const eventCounterRef = useRef(0);  // Add counter for unique IDs
  // Track content blocks for Anthropic SSE protocol
  const abortControllerRef = useRef<AbortController | null>(null);
  const contentBlocksRef = useRef<Record<number, { id: string, type: string, content: string }>>({});
  // Refs for auto-scrolling
  const thinkingScrollRef = useRef<HTMLDivElement>(null);
  const voiceScrollRef = useRef<HTMLDivElement>(null);
  const mobileThinkingScrollRef = useRef<HTMLDivElement>(null);
  const mobileVoiceScrollRef = useRef<HTMLDivElement>(null);
  
  // Instead of storing full events in state, just store the latest content
  const [thinkingContent, setThinkingContent] = useState<string>('');
  const [voiceContent, setVoiceContent] = useState<string>('');
  const [jsonContent, setJsonContent] = useState<string>('');
  const [structuredData, setStructuredData] = useState<any>(null);
  
  // Manage SSE connection
  const setupSSEConnection = useCallback((initType: 'welcome' | 'connect' | 'messages' = 'connect') => {
    // Clean up any existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Create a new abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    console.log(`Establishing SSE connection (${initType})...`);
    
    // Clear content blocks for new connection
    contentBlocksRef.current = {};
    
    fetchEventSource(`http://localhost:8111/agent/stream?init=${initType}`, {
      method: 'GET',
      headers: {
        'Accept': 'text/event-stream',
      },
      signal: abortController.signal,
      
      // Called when the connection is established
      onopen(response) {
        if (!response.ok) {
          throw new Error(`Failed to connect: ${response.status} ${response.statusText}`);
        }
        
        setIsConnected(true);
        console.log('SSE connection established');
        
        // Show connection notification for non-welcome connections
        if (initType !== 'welcome') {
          setSystemNotifications(prev => [...prev, {
            id: generateId(),
            content: 'Connected to server',
            timestamp: new Date()
          }]);
        }
        
        return Promise.resolve();
      },
      
      // Called for each event
      onmessage(event) {
        // Handle heartbeat messages
        if (event.data.trim() === ": heartbeat") {
          console.log('Received heartbeat');
          return;
        }
        
        try {
          // Parse the event data
          const data = JSON.parse(event.data) as AnthropicEvent;
          console.log(`Received ${event.event} event:`, data);
          
          // Handle different event types
          switch (event.event) {
            case 'content_block_start':
              if (data.content_block) {
                const { index, content_block } = data;
                const { type, id } = content_block;
                
                // Store new content block
                contentBlocksRef.current[index!] = {
                  id,
                  type,
                  content: ""
                };
                
                // Log for debugging
                console.log(`Content block start: index=${index}, type=${type}, id=${id}`);
                
                // Initialize UI based on content block type
                if (type === "text") {
                  setMessages(prev => {
                    // Only add a new message if the last message is from the user or no messages exist
                    if (prev.length === 0 || prev[prev.length - 1].isUser) {
                      return [...prev, {
                        id,
                        content: "",
                        isUser: false
                      }];
                    }
                    return prev;
                  });
                } else if (type === "thinking") {
                  // Reset thinking content when a new thinking block starts
                  setThinkingContent("");
                } else if (type === "voice") {
                  // Reset voice content when a new voice block starts
                  setVoiceContent("");
                }
              }
              break;
            
            case 'content_block_delta':
              if (data.delta && data.index !== undefined) {
                const { index, delta } = data;
                const { text } = delta;
                
                if (!contentBlocksRef.current[index]) {
                  console.warn(`Received delta for unknown content block ${index}`);
                  return;
                }
                
                // Update stored content
                contentBlocksRef.current[index].content += text || "";
                const blockType = contentBlocksRef.current[index].type;
                const blockId = contentBlocksRef.current[index].id;
                const blockContent = contentBlocksRef.current[index].content;
                
                // Log for debugging
                console.log(`Content block delta: type=${blockType}, delta_type=${delta.type}, text=${text}`);
                
                // Handle each delta type appropriately based on both block type and delta type
                if (text) {
                  // Create event object for history
                  const newEvent = {
                    id: generateId(),
                    content: text,
                    timestamp: new Date()
                  };
                  
                  // Use delta.type to determine which panel to update
                  const deltaType = delta.type;
                  
                  if (deltaType === "text_delta") {
                    // This should go to the main message panel
                    setMessages(prev => {
                      const messageIndex = prev.findIndex(msg => msg.id === blockId);
                      if (messageIndex >= 0) {
                        const updatedMessages = [...prev];
                        updatedMessages[messageIndex] = {
                          ...updatedMessages[messageIndex],
                          content: blockContent
                        };
                        return updatedMessages;
                      }
                      return prev;
                    });
                  } else if (deltaType === "thinking_delta") {
                    // Add to thinking events for history
                    setThinkingEvents(prev => [...prev, newEvent]);
                    // Accumulate thinking content
                    setThinkingContent(prev => prev + text);
                  } else if (deltaType === "voice_delta") {
                    // Add to voice events for history
                    setVoiceEvents(prev => [...prev, newEvent]);
                    // Accumulate voice content
                    setVoiceContent(prev => prev + text);
                  } else if (deltaType === "tool_delta") {
                    setToolEvents(prev => [...prev, newEvent]);
                  } else if (deltaType === "knowledge_delta") {
                    setKnowledgeEvents(prev => [...prev, newEvent]);
                  } else if (deltaType === "json_delta") {
                    // Progressive JSON accumulation
                    setJsonContent(prev => {
                      const newContent = prev + text;
                      
                      // Try to parse accumulated JSON
                      try {
                        const parsed = JSON.parse(newContent);
                        setStructuredData(parsed);
                        console.log('✅ JSON parsed successfully:', parsed);
                      } catch(e) {
                        // Still accumulating, not yet valid JSON
                        console.log('⏳ Accumulating JSON...', newContent.length, 'chars');
                      }
                      
                      return newContent;
                    });
                    
                    // Also add to knowledge events for history
                    setKnowledgeEvents(prev => [...prev, {
                      ...newEvent,
                      content: `JSON: ${text}`
                    }]);
                  } else if (deltaType === "error_delta") {
                    setSystemNotifications(prev => [...prev, {
                      ...newEvent,
                      isError: true
                    }]);
                  } else {
                    console.warn(`Unknown delta type: ${deltaType}`);
                  }
                }
              }
              break;
            
            case 'message_delta':
              if (data.delta?.stop_reason) {
                console.log(`Message completed with reason: ${data.delta.stop_reason}`);
              }
              break;
            
            case 'message_start':
              // Clear content from previous messages when a new message starts
              setThinkingContent("");
              setVoiceContent("");
              setJsonContent("");
              setStructuredData(null);
              setConductorEvents([]);
              
              // Log for debugging
              console.log(`Message start event received: ${JSON.stringify(data)}`);
              break;
            
            case 'system':
              // Handle system events from conductor orchestration
              const systemEvent = {
                id: generateId(),
                content: data.content || '',
                timestamp: new Date()
              };
              
              // Check if this is a conductor event
              const content = data.content || '';
              if (content.includes('🎼') || content.includes('Starting') || content.includes('Progress:') || 
                  content.includes('finished') || content.includes('All processes') || content.includes('Ready for')) {
                setConductorEvents(prev => [...prev, systemEvent]);
              } else {
                setSystemNotifications(prev => [...prev, systemEvent]);
              }
              break;
              
            // Handle legacy format or simple system messages
            default:
              const legacyData = data as AnthropicEvent & LegacyEventData;
              
              if (legacyData.type === 'system') {
                const systemEvent = {
                  id: generateId(),
                  content: legacyData.content || '',
                  timestamp: new Date()
                };
                
                // Check if this is a conductor event
                const content = legacyData.content || '';
                if (content.includes('🎼') || content.includes('Starting') || content.includes('Progress:') || 
                    content.includes('finished') || content.includes('All processes') || content.includes('Ready for')) {
                  setConductorEvents(prev => [...prev, systemEvent]);
                } else {
                  setSystemNotifications(prev => [...prev, systemEvent]);
                }
              } else if (legacyData.type === 'error') {
                setSystemNotifications(prev => [...prev, {
                  id: generateId(),
                  content: legacyData.content || (legacyData.error?.message) || 'Unknown error',
                  timestamp: new Date(),
                  isError: true
                }]);
              } else if (legacyData.type === 'message') {
                setMessages(prev => [...prev, {
                  id: generateId(),
                  content: legacyData.content || '',
                  isUser: false
                }]);
              }
              break;
          }
        } catch (error) {
          console.error('Error handling event:', error);
          setSystemNotifications(prev => [...prev, {
            id: generateId(),
            content: `Error processing event: ${error instanceof Error ? error.message : String(error)}`,
            timestamp: new Date(),
            isError: true
          }]);
        }
      },
      
      // Called when there is an error
      onerror(error) {
        console.error('SSE error:', error);
        
        // Add error notification
        setSystemNotifications(prev => [...prev, {
          id: generateId(),
          content: `Connection error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date(),
          isError: true
        }]);
        
        // Throw error to trigger reconnect
        throw error;
      },
      
      // Keep the connection open in hidden tabs
      openWhenHidden: true,
      
      // Configure retries (defined in the library)
      onclose() {
        console.log('SSE connection closed');
        setIsConnected(false);
        
        // Don't auto-reconnect for now - let user manually reconnect
        // This prevents the constant reconnection loop
        setSystemNotifications(prev => [...prev, {
          id: generateId(),
          content: 'Connection completed. Ready for new messages.',
          timestamp: new Date()
        }]);
        
        // Optional: Set a longer timeout to reconnect (disabled for now)
        // This prevents the constant reconnection loop that was causing issues
      }
    }).catch(error => {
      if (error.name !== 'AbortError') {
        console.error('Fatal SSE error:', error);
        setSystemNotifications(prev => [...prev, {
          id: generateId(),
          content: 'Failed to connect after multiple attempts. Please refresh.',
          timestamp: new Date(),
          isError: true
        }]);
      }
    });
  }, []);
  
  // Initialize connection on component mount
  useEffect(() => {
    // Start with welcome connection
    setupSSEConnection('welcome');
    
    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [setupSSEConnection]);
  
  // Function to handle sending a message
  const handleSendMessage = useCallback(async () => {
    if (inputText.trim()) {
      const uniqueId = generateId();
      
      const newMessage = {
        id: uniqueId,
        content: inputText,
        isUser: true
      };
      
      // Add user message to UI immediately
      setMessages(prev => [...prev, newMessage]);
      const userInput = inputText;
      setInputText('');
      
      try {
        // Send POST request
        const response = await fetch('http://localhost:8111/agent/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: userInput }),
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Set up SSE connection if needed
        if (!isConnected) {
          setupSSEConnection('connect');
        }
      } catch (error) {
        console.error('Error sending message:', error);
        
        // Add error notification
        setSystemNotifications(prev => [...prev, {
          id: generateId(),
          content: 'Failed to send message',
          timestamp: new Date(),
          isError: true
        }]);
      }
    }
  }, [inputText, isConnected, setupSSEConnection]);

  // Memoized setInputText to prevent unnecessary re-renders
  const handleInputChange = useCallback((text: string) => {
    setInputText(text);
  }, []);

  // Format timestamp for events
  const formatTime = (date: Date) => {
    // Calculate minutes elapsed
    const minutesElapsed = Math.round((new Date().getTime() - date.getTime()) / (1000 * 60));
    
    if (minutesElapsed <= 0) {
      return 'just now';
    } else if (minutesElapsed === 1) {
      return '1 minute ago';
    } else if (minutesElapsed < 60) {
      return `${minutesElapsed} minutes ago`;
    } else if (minutesElapsed < 24 * 60) {
      const hours = Math.floor(minutesElapsed / 60);
      return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
    } else {
      const days = Math.floor(minutesElapsed / (24 * 60));
      return `${days} ${days === 1 ? 'day' : 'days'} ago`;
    }
  };

  // Render a stream event
  const renderStreamEvent = (event: StreamEvent) => (
    <Card key={event.id} className="mb-3">
      <CardContent className="p-3">
        <p>{event.content}</p>
        <p className="text-sm text-muted-foreground mt-1">
          {formatTime(event.timestamp)}
        </p>
      </CardContent>
    </Card>
  );

  // Render a stream event with minimal styling for tools and system panels
  const renderMinimalEvent = (event: StreamEvent) => (
    <div key={event.id} className="mb-2 border-b border-border/30 pb-1">
      <p className="text-xs text-muted-foreground/70">{event.content}</p>
      <p className="text-[10px] text-muted-foreground/50 mt-0.5">
        {formatTime(event.timestamp)}
      </p>
    </div>
  );

  // Render streaming content for thinking and voice panels
  const renderStreamingContent = (content: string) => (
    <div className="text-xs italic text-muted-foreground whitespace-pre-wrap">
      {content}
    </div>
  );

  // Render a system notification
  const renderSystemNotification = (notification: SystemNotification) => (
    <Card key={notification.id} className={`mb-3 ${notification.isError ? 'border-red-500' : 'border-blue-500'}`}>
      <CardContent className="p-3">
        <div className="flex items-start">
          {notification.isError && <AlertTriangle className="h-4 w-4 text-red-500 mr-2 mt-1" />}
          <div>
            <p>{notification.content}</p>
            <p className="text-sm text-muted-foreground mt-1">
              {formatTime(notification.timestamp)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // Effect to auto-scroll thinking panels to bottom when new content arrives
  useEffect(() => {
    if (thinkingScrollRef.current) {
      thinkingScrollRef.current.scrollTop = thinkingScrollRef.current.scrollHeight;
    }
    if (mobileThinkingScrollRef.current) {
      mobileThinkingScrollRef.current.scrollTop = mobileThinkingScrollRef.current.scrollHeight;
    }
  }, [thinkingEvents]);

  // Effect to auto-scroll voice panels to bottom when new content arrives
  useEffect(() => {
    if (voiceScrollRef.current) {
      voiceScrollRef.current.scrollTop = voiceScrollRef.current.scrollHeight;
    }
    if (mobileVoiceScrollRef.current) {
      mobileVoiceScrollRef.current.scrollTop = mobileVoiceScrollRef.current.scrollHeight;
    }
  }, [voiceEvents]);

  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <div className="flex flex-col h-screen">
        {/* App header */}
        <div className="border-b p-2 flex justify-between items-center">
          <div className="flex items-center">
            {!isConnected && (
              <div className="text-red-500 flex items-center mr-2">
                <AlertTriangle className="h-4 w-4 mr-1" />
                <span className="text-xs">Disconnected</span>
              </div>
            )}
          </div>
          <ModeToggle />
        </div>
        
        {/* Main content area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Mobile view: Tabs for different streams */}
          <div className="md:hidden w-full">
            <Tabs defaultValue="data" className="w-full">
              <TabsList className="grid grid-cols-7 w-full">
                <TabsTrigger value="data">YesHuman</TabsTrigger>
                <TabsTrigger value="voice">Voice</TabsTrigger>
                <TabsTrigger value="thinking">Thinking</TabsTrigger>
                <TabsTrigger value="tools">Tools</TabsTrigger>
                <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
                <TabsTrigger value="conductor">Conductor</TabsTrigger>
                <TabsTrigger value="system">System</TabsTrigger>
              </TabsList>
              
              <TabsContent value="data" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none flex flex-col">
                  <CardHeader className="px-4 py-2 flex flex-row items-center justify-between">
                    <CardTitle>YesHuman</CardTitle>
                    <div className="flex items-center space-x-2">
                      <Switch 
                        id="shortcut-mode-mobile" 
                        checked={shortcutMode}
                        onCheckedChange={setShortcutMode}
                      />
                      <Label htmlFor="shortcut-mode-mobile" className="text-xs">Ctrl+Enter mode</Label>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4 flex-1 overflow-hidden">
                    <ScrollArea className="h-[calc(100vh-230px)] no-scrollbar">
                      <div className="space-y-4">
                        {messages.map(message => (
                          <div key={message.id} className={`flex items-start gap-4 ${message.isUser ? 'flex-row-reverse' : ''}`}>
                            <Avatar>
                              <AvatarImage src={message.isUser ? "/avatar2.png" : "/avatar1.png"} />
                              <AvatarFallback>{message.isUser ? 'U' : 'B'}</AvatarFallback>
                            </Avatar>
                            <Card className="flex-1">
                              <CardContent className="p-3">
                                <p style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>
                              </CardContent>
                            </Card>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                  <CardFooter className="p-0 border-t">
                    <ChatInput 
                      inputText={inputText} 
                      setInputText={handleInputChange} 
                      handleSendMessage={handleSendMessage}
                      shortcutMode={shortcutMode}
                    />
                  </CardFooter>
                </Card>
              </TabsContent>
              
              <TabsContent value="voice" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none">
                  <CardHeader className="px-4 py-2 flex flex-row items-center justify-between">
                    <CardTitle>Voice</CardTitle>
                    <div className="flex items-center space-x-2">
                      <Switch 
                        id="audio-mode" 
                        checked={audioEnabled}
                        onCheckedChange={setAudioEnabled}
                      />
                      <Label htmlFor="audio-mode">Audio</Label>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div 
                      ref={mobileVoiceScrollRef}
                      className="h-[calc(100vh-200px)] flex flex-col overflow-y-auto p-2 no-scrollbar"
                    >
                      <div className="flex-1"></div>
                      <div className="mt-auto">
                        {renderStreamingContent(voiceContent)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="thinking" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none">
                  <CardHeader className="px-4 py-2">
                    <CardTitle>Thinking</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div 
                      ref={mobileThinkingScrollRef}
                      className="h-[calc(100vh-200px)] flex flex-col overflow-y-auto p-2 no-scrollbar"
                    >
                      <div className="flex-1"></div>
                      <div className="mt-auto">
                        {renderStreamingContent(thinkingContent)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="tools" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none">
                  <CardHeader className="px-4 py-2">
                    <CardTitle>Tools</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="h-[calc(100vh-200px)] overflow-y-auto no-scrollbar">
                      <div>
                        {[...toolEvents].reverse().map(renderMinimalEvent)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="knowledge" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none">
                  <CardHeader className="px-4 py-2">
                    <CardTitle>Knowledge</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="h-[calc(100vh-200px)] overflow-y-auto no-scrollbar">
                      {/* Structured Data Display */}
                      {structuredData && (
                        <div className="mb-4 p-3 bg-muted rounded-lg">
                          <h4 className="text-sm font-semibold mb-2">Structured Data:</h4>
                          <pre className="text-xs whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(structuredData, null, 2)}
                          </pre>
                        </div>
                      )}
                      
                      {/* JSON Accumulation Progress */}
                      {jsonContent && !structuredData && (
                        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                          <h4 className="text-sm font-semibold mb-2">JSON Accumulating... ({jsonContent.length} chars)</h4>
                          <pre className="text-xs text-muted-foreground whitespace-pre-wrap overflow-x-auto max-h-20">
                            {jsonContent}
                          </pre>
                        </div>
                      )}
                      
                      {/* Knowledge Events History */}
                      <div className="space-y-2">
                        {knowledgeEvents.map(renderStreamEvent)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="conductor" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none">
                  <CardHeader className="px-4 py-2">
                    <CardTitle className="flex items-center gap-2">
                      🎼 Conductor
                      <span className="text-xs text-muted-foreground">
                        ({conductorEvents.length} events)
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="h-[calc(100vh-200px)] overflow-y-auto no-scrollbar">
                      <div>
                        {[...conductorEvents].reverse().map(event => (
                          <div key={event.id} className="mb-3 p-2 rounded-lg bg-muted/30 border border-border/20">
                            <div className="flex items-start">
                              <div className="flex-1">
                                <p className="text-sm font-medium text-foreground/90">{event.content}</p>
                                <p className="text-xs text-muted-foreground/60 mt-1">
                                  {formatTime(event.timestamp)}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {conductorEvents.length === 0 && (
                          <div className="text-center text-muted-foreground/50 text-xs py-8">
                            <div className="mb-2">🎼</div>
                            <p>Conductor orchestration events will appear here</p>
                            <p className="mt-1">Parallel process coordination • Progress tracking • Status updates</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="system" className="h-[calc(100vh-150px)]">
                <Card className="h-full border-0 rounded-none">
                  <CardHeader className="px-4 py-2">
                    <CardTitle>System</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="h-[calc(100vh-200px)] overflow-y-auto no-scrollbar">
                      <div>
                        {[...systemNotifications].reverse().map(notification => (
                          <div key={notification.id} className="mb-2 border-b border-border/30 pb-1">
                            <div className="flex items-start">
                              {notification.isError && <AlertTriangle className="h-3 w-3 text-red-500/70 mr-1 mt-0.5" />}
                              <div>
                                <p className="text-xs text-muted-foreground/70">{notification.content}</p>
                                <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                                  {formatTime(notification.timestamp)}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
          
          {/* Desktop view: Multi-column layout */}
          <div className="hidden md:flex w-full h-full">
            {/* Chat column */}
            <div className="w-1/2 border-r">
              <Card className="h-full border-0 rounded-none flex flex-col">
                <CardHeader className="px-4 py-2 flex flex-row items-center justify-between">
                  <CardTitle>YesHuman</CardTitle>
                  <div className="flex items-center space-x-2">
                    <Switch 
                      id="shortcut-mode-desktop" 
                      checked={shortcutMode}
                      onCheckedChange={setShortcutMode}
                    />
                    <Label htmlFor="shortcut-mode-desktop" className="text-xs">Ctrl+Enter mode</Label>
                  </div>
                </CardHeader>
                <CardContent className="p-4 flex-1 overflow-hidden">
                  <ScrollArea className="h-[calc(100vh-180px)] no-scrollbar">
                    <div className="space-y-4">
                      {messages.map(message => (
                        <div key={message.id} className={`flex items-start gap-4 ${message.isUser ? 'flex-row-reverse' : ''}`}>
                          <Avatar className="h-8 w-8">
                            <AvatarImage src={message.isUser ? "/avatar2.png" : "/avatar1.png"} />
                            <AvatarFallback>{message.isUser ? 'U' : 'B'}</AvatarFallback>
                          </Avatar>
                          <Card className="flex-1">
                            <CardContent className="p-2 text-sm">
                              <p style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>
                            </CardContent>
                          </Card>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
                <CardFooter className="p-0 border-t">
                  <ChatInput 
                    inputText={inputText} 
                    setInputText={handleInputChange} 
                    handleSendMessage={handleSendMessage}
                    shortcutMode={shortcutMode}
                  />
                </CardFooter>
              </Card>
            </div>
            
            {/* Side columns */}
            <div className="w-1/2 flex flex-col">
              {/* Top row: Thinking and Voice */}
              <div className="flex flex-1 border-b">
                {/* Thinking column */}
                <div className="w-1/2 border-r">
                  <Card className="h-full border-0 rounded-none">
                    <CardHeader className="px-4 py-2">
                      <CardTitle>Thinking</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div 
                        ref={thinkingScrollRef}
                        className="h-[calc(100vh/2-100px)] flex flex-col overflow-y-auto p-2 no-scrollbar"
                      >
                        <div className="flex-1"></div>
                        <div className="mt-auto">
                          {renderStreamingContent(thinkingContent)}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                
                {/* Voice column */}
                <div className="w-1/2">
                  <Card className="h-full border-0 rounded-none">
                    <CardHeader className="px-4 py-2 flex flex-row items-center justify-between">
                      <CardTitle>Voice</CardTitle>
                      <div className="flex items-center space-x-2">
                        <Switch 
                          id="desktop-audio-mode" 
                          checked={audioEnabled}
                          onCheckedChange={setAudioEnabled}
                        />
                        <Label htmlFor="desktop-audio-mode" className="text-xs">Audio</Label>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div 
                        ref={voiceScrollRef}
                        className="h-[calc(100vh/2-100px)] flex flex-col overflow-y-auto p-2 no-scrollbar"
                      >
                        <div className="flex-1"></div>
                        <div className="mt-auto">
                          {renderStreamingContent(voiceContent)}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
              
              {/* Bottom row: Tools, Conductor, and System */}
              <div className="flex flex-1">
                {/* Tools column */}
                <div className="w-1/3 border-r">
                  <Card className="h-full border-0 rounded-none">
                    <CardHeader className="px-4 py-2">
                      <CardTitle>Tools</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div className="h-[calc(100vh/2-100px)] overflow-y-auto no-scrollbar">
                        <div>
                          {[...toolEvents].reverse().map(renderMinimalEvent)}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                
                {/* Conductor column */}
                <div className="w-1/3 border-r">
                  <Card className="h-full border-0 rounded-none">
                    <CardHeader className="px-4 py-2">
                      <CardTitle className="flex items-center gap-2">
                        🎼 Conductor
                        <span className="text-xs text-muted-foreground">
                          ({conductorEvents.length})
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div className="h-[calc(100vh/2-100px)] overflow-y-auto no-scrollbar">
                        <div>
                          {[...conductorEvents].reverse().map(event => (
                            <div key={event.id} className="mb-2 p-1.5 rounded bg-muted/20 border border-border/20">
                              <p className="text-xs font-medium text-foreground/90">{event.content}</p>
                              <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                                {formatTime(event.timestamp)}
                              </p>
                            </div>
                          ))}
                          {conductorEvents.length === 0 && (
                            <div className="text-center text-muted-foreground/50 text-xs py-4">
                              <div className="mb-1">🎼</div>
                              <p>Orchestration</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                
                {/* System notifications column */}
                <div className="w-1/3">
                  <Card className="h-full border-0 rounded-none">
                    <CardHeader className="px-4 py-2">
                      <CardTitle>System</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div className="h-[calc(100vh/2-100px)] overflow-y-auto no-scrollbar">
                        <div>
                          {[...systemNotifications].reverse().map(notification => (
                            <div key={notification.id} className="mb-2 border-b border-border/30 pb-1">
                              <div className="flex items-start">
                                {notification.isError && <AlertTriangle className="h-3 w-3 text-red-500/70 mr-1 mt-0.5" />}
                                <div>
                                  <p className="text-xs text-muted-foreground/70">{notification.content}</p>
                                  <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                                    {formatTime(notification.timestamp)}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ThemeProvider>
  )
}

export default App
