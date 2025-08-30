import { Volume2 } from 'lucide-react';

interface VoicePanelProps {
  voiceLines: string[];
}

export const VoicePanel = ({ voiceLines }: VoicePanelProps) => {
  return (
    <div className="w-1/2 border-b p-4">
      <div className="flex items-center mb-2">
        <Volume2 className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        {voiceLines.map((line, i) => (
          <div key={i} className="text-xs text-muted-foreground/70 italic">
            {line}
          </div>
        ))}
      </div>
    </div>
  );
};
