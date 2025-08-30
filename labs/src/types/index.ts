// Core types for SSE events
export interface ContentBlock {
  type: string;
  id: string;
  content: string;
}

export interface SSEEvent {
  event: string;
  data: any;
}

export interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
}

// Animation types
export interface AnimationTrigger {
  (triggerFn: () => void): void;
}

// Theme types
export type ThemeMode = 'light' | 'dark' | 'system';

export interface ThemeTitles {
  light: string;
  dark: string;
  system: string;
}
