import { Bot, User, Plane, Leaf, Heart } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';
import { CURRENT_CLIENT } from '../../constants';

// Helper function to get the appropriate icon component
const getBrandIcon = (iconName: string) => {
  switch (iconName) {
    case 'Bot':
      return Bot;
    case 'Plane':
      return Plane;
    case 'Leaf':
      return Leaf;
    case 'Heart':
      return Heart;
    default:
      return Bot; // fallback to Bot
  }
};

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  return (
    <div className={`flex gap-3 ${message.isUser ? 'flex-row-reverse' : ''}`}>
      <div className="w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground">
        {message.isUser ? (
          <User className="h-4 w-4" />
        ) : (
          (() => {
            const IconComponent = getBrandIcon(CURRENT_CLIENT.brandIcon || 'Bot');
            return <IconComponent className="h-4 w-4" />;
          })()
        )}
      </div>
      <div className="flex-1 bg-muted/50 rounded-lg p-3">
        <div className="whitespace-pre-wrap text-sm">
          {message.content}
        </div>
      </div>
    </div>
  );
};
