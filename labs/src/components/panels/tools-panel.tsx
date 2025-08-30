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
    <div className="w-1/2 border-r p-4">
      <div className="flex items-center mb-2">
        <Wrench className="h-4 w-4 text-muted-foreground" />
      </div>
      {/* Display active tools as icons */}
      <div className="flex flex-wrap gap-2">
        {activeTools.map((tool, index) => (
          <div key={index} className="flex items-center space-x-1">
            {getToolIcon(tool)}
          </div>
        ))}
      </div>
    </div>
  );
};
