import { Bot, User } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  return (
    <div className={`flex gap-3 ${message.isUser ? 'flex-row-reverse' : ''}`}>
      <div className="w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground">
        {message.isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="flex-1 bg-muted/50 rounded-lg p-3">
        <div className="whitespace-pre-wrap text-sm">
          {message.content}
        </div>
      </div>
    </div>
  );
};
