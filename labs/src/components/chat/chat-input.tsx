import { useCallback } from 'react';
import { AnimatedSendButton } from '../animated-send-button';

interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
}

export const ChatInput = ({ inputText, setInputText, onSubmit, isLoading = false }: ChatInputProps) => {
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey && !isLoading) {
      e.preventDefault();
      onSubmit();
    }
  }, [onSubmit, isLoading]);

  return (
    <div className="border-t p-4">
      <div className="flex gap-2">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Ctrl+Enter to send)"
          className="flex-1 resize-none border rounded-md p-2 min-h-[60px] text-sm bg-background"
          rows={2}
          disabled={false}
        />
        <AnimatedSendButton
          onClick={onSubmit}
          disabled={!inputText.trim() || isLoading}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};
