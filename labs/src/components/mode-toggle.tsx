import { useTheme } from './theme-provider';
import { Button } from './ui/button';
import { Moon, Sun, Monitor } from 'lucide-react';
import type { ThemeTitles } from '../types';

export const ModeToggle = () => {
  const { theme, setTheme } = useTheme();
  
  const nextTheme = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light';
  const titles: ThemeTitles = {
    light: 'Switch to dark mode',
    dark: 'Switch to system mode', 
    system: 'Switch to light mode'
  };
  
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(nextTheme)}
      className="h-8 w-8"
      title={titles[theme]}
    >
      {theme === 'light' && <Sun className="h-4 w-4" />}
      {theme === 'dark' && <Moon className="h-4 w-4" />}
      {theme === 'system' && <Monitor className="h-4 w-4" />}
      <span className="sr-only">
        Current: {theme} mode. Click to switch to {nextTheme} mode.
      </span>
    </Button>
  );
};
