import { Brain } from 'lucide-react';

interface MemoryPanelProps {
  memorySummaries: string[];
}

export const MemoryPanel = ({ memorySummaries }: MemoryPanelProps) => {
  return (
    <div className="flex-1 border-b p-4 overflow-hidden flex flex-col">
      <div className="flex items-center mb-2 flex-shrink-0">
        <Brain className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium ml-2">Memories</span>
      </div>
      <div className="space-y-1 flex-1 overflow-auto">
        {memorySummaries.map((summary, i) => (
          <div key={i} className="text-xs text-muted-foreground/70 italic">
            {summary}
          </div>
        ))}
      </div>
    </div>
  );
};




