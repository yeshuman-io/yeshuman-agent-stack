import { useEffect, useRef } from 'react';
import { ChatMessage } from './chat-message';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatMessagesProps {
  messages: ChatMessageType[];
  onFeedback?: (runId: string, score?: number, tags?: string[], comment?: string) => void;
}

export const ChatMessages = ({ messages, onFeedback }: ChatMessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [messages]);

  return (
    <div 
      ref={messagesContainerRef}
      className="flex-1 p-4 overflow-y-auto scroll-smooth min-h-0 custom-scrollbar"
    >
      <div className="space-y-4">
        {messages.map(message => (
          <ChatMessage key={message.id} message={message} onFeedback={onFeedback} />
        ))}
        {/* Invisible element at the bottom to scroll to */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
