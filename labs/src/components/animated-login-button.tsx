import { useEffect, useState } from 'react';
import {
  LogIn,
  Shield,
  Key,
  Lock,
  Unlock,
  UserCheck,
  CheckCircle,
  Fingerprint,
  Eye,
  EyeOff,
  BadgeCheck,
  // System/transmission icons
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
  Router,
  Rss,
  Share,
  ShareIcon,
  Podcast
} from 'lucide-react';

interface AnimatedLoginButtonProps {
  onClick?: () => void;
  disabled: boolean;
  isLoading: boolean;
}

// Login/authentication related icons to cycle through
const loginIcons = [
  LogIn,
  Shield,
  Key,
  Lock,
  Unlock,
  UserCheck,
  CheckCircle,
  Fingerprint,
  Eye,
  EyeOff,
  BadgeCheck
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

export const AnimatedLoginButton = ({ onClick, disabled, isLoading }: AnimatedLoginButtonProps) => {
  const [currentIcon, setCurrentIcon] = useState(0);
  const [currentSystemIcon, setCurrentSystemIcon] = useState(0);
  const [currentGlyph, setCurrentGlyph] = useState(0);
  const [displayType, setDisplayType] = useState<'login' | 'system' | 'glyph'>('login');

  useEffect(() => {
    if (!isLoading) {
      // Reset to default LogIn icon when not loading
      setCurrentIcon(0);
      setCurrentSystemIcon(0);
      setCurrentGlyph(0);
      setDisplayType('login');
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
        // 40% chance to show a login icon
        setDisplayType('login');
        setCurrentIcon(Math.floor(Math.random() * loginIcons.length));
      }
    }, 120); // Fast 120ms cycle

    return () => clearInterval(interval);
  }, [isLoading]);

  const CurrentLoginIcon = loginIcons[currentIcon];
  const CurrentSystemIcon = systemIcons[currentSystemIcon];

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      type="submit"
      className="w-full p-2 bg-primary text-primary-foreground rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-all duration-75"
    >
      {isLoading ? (
        displayType === 'login' ? (
          <CurrentLoginIcon className="h-4 w-4 transition-all duration-75" />
        ) : displayType === 'system' ? (
          <CurrentSystemIcon className="h-4 w-4 transition-all duration-75" />
        ) : (
          <span className="text-sm font-mono leading-none transition-all duration-75">
            {textGlyphs[currentGlyph]}
          </span>
        )
      ) : (
        <LogIn className="h-4 w-4" />
      )}
    </button>
  );
};
