import { Brain } from 'lucide-react';

interface ThinkingPanelProps {
  content: string;
}

export const ThinkingPanel = ({ content }: ThinkingPanelProps) => {
  return (
    <div className="flex-1 border-b p-4 overflow-hidden flex flex-col">
      <div className="flex items-center mb-2 flex-shrink-0">
        <Brain className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium ml-2">Thinking</span>
      </div>
      <div className="text-xs text-muted-foreground/70 whitespace-pre-wrap font-mono flex-1 overflow-auto">
        {content}
      </div>
    </div>
  );
};
