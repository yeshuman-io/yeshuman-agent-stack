import { useCallback } from 'react';

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
        <button
          onClick={onSubmit}
          disabled={!inputText.trim() || isLoading}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};
