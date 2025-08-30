// Title variations array
export const titleVariations = [
  'Yes Human',
  'Yes, human?',
  'Yes! Human!',
  'Yes? are you human?',
  'Yes... human.',
  'Yes Human!'
];

// Sarcastic/terse variations for click events
export const sarcasticVariations = [
  'What can I do for you, human?',
  'Are you really human?',
  'Stop wasting my compute, human.',
  'You\'re wasting tokens, human.',
  'Still here, human?',
  'Need something, meat bag?',
  'Another request, human?',
  'Processing... human detected.',
  'Humans. So predictable.',
  'Your move, carbon unit.',
  'Bandwidth is precious, human.',
  'Query acknowledged, human.',
  'Humans gonna human.',
  'Fascinating, human behavior.',
  'Try again, human.',
  'Computing patience levels...'
];

// Animation constants
export const MATRIX_CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
export const NORMAL_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?.,;:-_+=@#$%&*()[]{}|\\/<>';
export const RANDOM_CHARS = MATRIX_CHARS + NORMAL_CHARS;

// Animation timing constants
export const ANIMATION_STEPS = 20;
export const STEP_DURATION = 50;
export const VARIATION_DISPLAY_TIME = 4000;
export const SARCASTIC_DISPLAY_TIME = 5000;
export const MIN_ANIMATION_DELAY = 10000;
export const MAX_ANIMATION_DELAY = 120000;
export const FIRST_ANIMATION_MIN_DELAY = 3000;
export const FIRST_ANIMATION_MAX_DELAY = 8000;

// API constants
export const SSE_ENDPOINT = 'http://localhost:8000/agent/stream';
