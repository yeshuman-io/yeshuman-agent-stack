import { Volume2 } from 'lucide-react';

interface VoicePanelProps {
  voiceLines: string[];
}

export const VoicePanel = ({ voiceLines }: VoicePanelProps) => {
  return (
    <div className="flex-1 border-b p-4 overflow-hidden flex flex-col">
      <div className="flex items-center mb-2 flex-shrink-0">
        <Volume2 className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium ml-2">Voice</span>
      </div>
      <div className="space-y-1 flex-1 overflow-auto">
        {voiceLines.map((line, i) => (
          <div key={i} className="text-xs text-muted-foreground/70 italic">
            {line}
          </div>
        ))}
      </div>
    </div>
  );
};
