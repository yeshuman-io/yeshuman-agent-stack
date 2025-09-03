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
  Play,
  FastForward,
  // Additional transmission/system icons
  Antenna,
  Cast,
  Database,
  HardDrive,
  Layers,
  Network,
  Satellite,
  Server,
  Signal,
  Terminal,
  Upload,
  Download,
  RefreshCw,
  RotateCcw,
  Power,
  Cpu,
  MonitorSpeaker,
  Waves,
  // Additional valid icons
  Router,
  Rss,
  Share,
  ShareIcon,
  Podcast
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

// System/transmission related icons for matrix animation
const systemIcons = [
  Antenna, Cast, Database, HardDrive, Layers, Network, Satellite,
  Server, Signal, Terminal, Upload, Download, RefreshCw, RotateCcw,
  Power, Cpu, MonitorSpeaker, Waves, Router, Rss, Share, ShareIcon, Podcast
];

// Text-based matrix glyphs (Unicode characters + Japanese katakana)
const textGlyphs = [
  // Japanese katakana (from animated title)
  'ア', 'イ', 'ウ', 'エ', 'オ', 'カ', 'キ', 'ク', 'ケ', 'コ', 'サ', 'シ', 'ス', 'セ', 'ソ',
  'タ', 'チ', 'ツ', 'テ', 'ト', 'ナ', 'ニ', 'ヌ', 'ネ', 'ノ', 'ハ', 'ヒ', 'フ', 'ヘ', 'ホ',
  'マ', 'ミ', 'ム', 'メ', 'モ', 'ヤ', 'ユ', 'ヨ', 'ラ', 'リ', 'ル', 'レ', 'ロ', 'ワ', 'ヲ', 'ン',
  // Braille patterns
  '⠀', '⠁', '⠂', '⠃', '⠄', '⠅', '⠆', '⠇', '⠈', '⠉', '⠊', '⠋', '⠌', '⠍', '⠎', '⠏',
  '⠐', '⠑', '⠒', '⠓', '⠔', '⠕', '⠖', '⠗', '⠘', '⠙', '⠚', '⠛', '⠜', '⠝', '⠞', '⠟',
  '⣀', '⣁', '⣂', '⣃', '⣄', '⣅', '⣆', '⣇', '⣈', '⣉', '⣊', '⣋', '⣌', '⣍', '⣎', '⣏',
  // Geometric shapes
  '◐', '◑', '◒', '◓', '◔', '◕', '◖', '◗', '◘', '◙', '◚', '◛', '◜', '◝', '◞', '◟',
  // Block elements
  '▀', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▉', '▊', '▋', '▌', '▍', '▎', '▏',
  // Box drawing
  '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '│', '─', '╭', '╮', '╰', '╯', '╱', '╲'
];

export const AnimatedSendButton = ({ onClick, disabled, isLoading }: AnimatedSendButtonProps) => {
  const [currentIcon, setCurrentIcon] = useState(0);
  const [currentSystemIcon, setCurrentSystemIcon] = useState(0);
  const [currentGlyph, setCurrentGlyph] = useState(0);
  const [displayType, setDisplayType] = useState<'send' | 'system' | 'glyph'>('send');

  useEffect(() => {
    if (!isLoading) {
      // Reset to default Send icon when not loading
      setCurrentIcon(0);
      setCurrentSystemIcon(0);
      setCurrentGlyph(0);
      setDisplayType('send');
      return;
    }

    // Fast animation cycle when loading
    const interval = setInterval(() => {
      const random = Math.random();
      
      if (random > 0.7) {
        // 30% chance to show a text glyph
        setDisplayType('glyph');
        setCurrentGlyph(Math.floor(Math.random() * textGlyphs.length));
      } else if (random > 0.4) {
        // 30% chance to show a system icon
        setDisplayType('system');
        setCurrentSystemIcon(Math.floor(Math.random() * systemIcons.length));
      } else {
        // 40% chance to show a send icon
        setDisplayType('send');
        setCurrentIcon(Math.floor(Math.random() * sendIcons.length));
      }
    }, 120); // Fast 120ms cycle

    return () => clearInterval(interval);
  }, [isLoading]);

  const CurrentSendIcon = sendIcons[currentIcon];
  const CurrentSystemIcon = systemIcons[currentSystemIcon];

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="p-2 bg-primary text-primary-foreground rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center w-8 h-8 self-start transition-all duration-75"
    >
      {isLoading ? (
        displayType === 'send' ? (
          <CurrentSendIcon className="h-3 w-3 transition-all duration-75" />
        ) : displayType === 'system' ? (
          <CurrentSystemIcon className="h-3 w-3 transition-all duration-75" />
        ) : (
          <span className="text-xs font-mono leading-none transition-all duration-75">
            {textGlyphs[currentGlyph]}
          </span>
        )
      ) : (
        <Send className="h-3 w-3" />
      )}
    </button>
  );
};
