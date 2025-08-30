import { useEffect, useState } from 'react';
import { 
  Send, 
  Zap, 
  ArrowRight, 
  ChevronRight, 
  ArrowUpRight, 
  MessageCircle, 
  Radio,
  Activity,
  Wifi,
  Globe,
  Link,
  Circle,
  Play,
  FastForward
} from 'lucide-react';

interface AnimatedSendButtonProps {
  onClick: () => void;
  disabled: boolean;
  isLoading: boolean;
}

// Send-like icons to cycle through
const sendIcons = [
  Send, 
  Zap, 
  ArrowRight, 
  ChevronRight, 
  ArrowUpRight, 
  MessageCircle, 
  Radio,
  Activity,
  Wifi,
  Globe,
  Link,
  Play,
  FastForward
];

// Matrix-like glyphs (using Unicode characters)
const matrixGlyphs = [
  '⠀', '⠁', '⠂', '⠃', '⠄', '⠅', '⠆', '⠇', '⠈', '⠉', '⠊', '⠋', '⠌', '⠍', '⠎', '⠏',
  '⠐', '⠑', '⠒', '⠓', '⠔', '⠕', '⠖', '⠗', '⠘', '⠙', '⠚', '⠛', '⠜', '⠝', '⠞', '⠟',
  '⣀', '⣁', '⣂', '⣃', '⣄', '⣅', '⣆', '⣇', '⣈', '⣉', '⣊', '⣋', '⣌', '⣍', '⣎', '⣏',
  '◐', '◑', '◒', '◓', '◔', '◕', '◖', '◗', '◘', '◙', '◚', '◛', '◜', '◝', '◞', '◟',
  '▀', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▉', '▊', '▋', '▌', '▍', '▎', '▏',
  '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '│', '─', '╭', '╮', '╰', '╯', '╱', '╲'
];

export const AnimatedSendButton = ({ onClick, disabled, isLoading }: AnimatedSendButtonProps) => {
  const [currentIcon, setCurrentIcon] = useState(0);
  const [currentGlyph, setCurrentGlyph] = useState(0);
  const [showIcon, setShowIcon] = useState(true);

  useEffect(() => {
    if (!isLoading) {
      // Reset to default Send icon when not loading
      setCurrentIcon(0);
      setCurrentGlyph(0);
      setShowIcon(true);
      return;
    }

    // Fast animation cycle when loading
    const interval = setInterval(() => {
      if (Math.random() > 0.6) {
        // 40% chance to show a matrix glyph
        setShowIcon(false);
        setCurrentGlyph(Math.floor(Math.random() * matrixGlyphs.length));
      } else {
        // 60% chance to show a send icon
        setShowIcon(true);
        setCurrentIcon(Math.floor(Math.random() * sendIcons.length));
      }
    }, 120); // Fast 120ms cycle

    return () => clearInterval(interval);
  }, [isLoading]);

  const CurrentIcon = sendIcons[currentIcon];

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="p-2 bg-primary text-primary-foreground rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center w-8 h-8 self-start transition-all duration-75"
    >
      {isLoading ? (
        showIcon ? (
          <CurrentIcon className="h-3 w-3 transition-all duration-75" />
        ) : (
          <span className="text-xs font-mono leading-none transition-all duration-75">
            {matrixGlyphs[currentGlyph]}
          </span>
        )
      ) : (
        <Send className="h-3 w-3" />
      )}
    </button>
  );
};
