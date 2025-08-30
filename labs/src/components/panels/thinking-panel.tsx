import { Brain } from 'lucide-react';

interface ThinkingPanelProps {
  content: string;
}

export const ThinkingPanel = ({ content }: ThinkingPanelProps) => {
  return (
    <div className="w-1/2 border-r border-b p-4">
      <div className="flex items-center mb-2">
        <Brain className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="text-xs text-muted-foreground/70 whitespace-pre-wrap font-mono">
        {content}
      </div>
    </div>
  );
};
