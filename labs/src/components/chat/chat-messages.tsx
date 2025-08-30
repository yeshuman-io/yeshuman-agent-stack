import { ChatMessage } from './chat-message';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatMessagesProps {
  messages: ChatMessageType[];
}

export const ChatMessages = ({ messages }: ChatMessagesProps) => {
  return (
    <div className="flex-1 p-4 overflow-y-auto">
      <div className="space-y-4">
        {messages.map(message => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
};
