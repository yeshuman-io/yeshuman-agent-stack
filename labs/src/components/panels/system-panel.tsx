import { Terminal } from 'lucide-react';

interface SystemPanelProps {
  systemLogs: string[];
}

export const SystemPanel = ({ systemLogs }: SystemPanelProps) => {
  return (
    <div className="flex-1 p-4 overflow-hidden flex flex-col">
      <div className="flex items-center mb-2 flex-shrink-0">
        <Terminal className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium ml-2">System</span>
      </div>
      <div className="space-y-1 flex-1 overflow-auto">
        {systemLogs.map((log, i) => (
          <div key={i} className="text-xs text-muted-foreground/70">
            {log}
          </div>
        ))}
      </div>
    </div>
  );
};
