import { Wrench, Cloud, Calculator } from 'lucide-react';

interface ToolsPanelProps {
  activeTools: string[];
}

// Helper function to get icon for tool type
const getToolIcon = (toolName: string) => {
  switch (toolName.toLowerCase()) {
    case 'weather':
      return <Cloud className="h-4 w-4 text-muted-foreground" />;
    case 'calculator':
      return <Calculator className="h-4 w-4 text-muted-foreground" />;
    default:
      return <Wrench className="h-4 w-4 text-muted-foreground" />;
  }
};

export const ToolsPanel = ({ activeTools }: ToolsPanelProps) => {
  return (
    <div className="flex-1 border-b p-4 overflow-hidden flex flex-col">
      <div className="flex items-center mb-2 flex-shrink-0">
        <Wrench className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium ml-2">Tools</span>
      </div>
      {/* Display active tools as icons */}
      <div className="flex flex-wrap gap-2 flex-1 overflow-auto">
        {activeTools.map((tool, index) => (
          <div key={index} className="flex items-center space-x-1">
            {getToolIcon(tool)}
          </div>
        ))}
      </div>
    </div>
  );
};
