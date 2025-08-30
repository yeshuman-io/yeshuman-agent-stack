import { Terminal } from 'lucide-react';

interface SystemPanelProps {
  systemLogs: string[];
}

export const SystemPanel = ({ systemLogs }: SystemPanelProps) => {
  return (
    <div className="w-1/2 p-4">
      <div className="flex items-center mb-2">
        <Terminal className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        {systemLogs.map((log, i) => (
          <div key={i} className="text-xs text-muted-foreground/70">
            {log}
          </div>
        ))}
      </div>
    </div>
  );
};
