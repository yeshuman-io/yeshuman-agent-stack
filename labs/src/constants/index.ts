// Client configuration
const CLIENT_CONFIG = import.meta.env.VITE_CLIENT_CONFIG || 'yeshuman';

// API configuration for backend connection
// VITE_API_URL: Set to backend URL for cross-domain requests (optional)
// Leave empty for same-domain requests (recommended for production)
// Example: https://your-backend-api.com
export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Client-specific configurations
export const CLIENT_CONFIGS = {
  yeshuman: {
    name: 'Yes Human',
    brand: 'Yes Human',
    logoPath: '',
    brandIcon: 'Bot',
    faviconPath: '/favicon.svg',
    primaryColor: '#3b82f6',
    welcomeMessage: 'Yes, welcome human.',
    tagline: 'Human Compute Interface',
    placeholderEmail: 'human@sentient.ai',
    placeholderPassword: 'Enter your precious password',
    loginLabel: 'Human?',
    loginSubheader: 'Enter your precious credentials to interact with me, human.',
    logoutLabel: 'Human',
    logoutDescription: 'Return to anonymity',
    description: "Don't have an account? Contact an administrator to get access to Yes Human.",
    titleVariations: [
      'Yes Human',
      'Yes, human?',
      'Yes! Human!',
      'Yes? are you human?',
      'Yes... human.',
      'Yes Human!'
    ],
    sarcasticVariations: [
      'What can I do for you, human?',
      'Are you really human?',
      'Stop wasting my compute, human.',
      'You\'re wasting tokens, human.',
      'Still here, human?',
      'Did something go wrong with your biological neural network?',
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
    ],
  },
  bookedai: {
    name: 'Booked AI',
    brand: 'Booked AI',
    logoPath: '',
    brandIcon: 'Plane',
    faviconPath: '/favicon.svg',
    primaryColor: '#10b981',
    welcomeMessage: 'Welcome to Booked AI.',
    tagline: 'Your AI travel companion',
    placeholderEmail: 'traveler@booked.ai',
    placeholderPassword: 'Your passport to adventure',
    loginLabel: 'Traveler?',
    loginSubheader: 'Enter your credentials to unlock your next journey.',
    logoutLabel: 'Traveler',
    logoutDescription: 'Return to reality',
    description: "Don't have an account? Contact your administrator to get access to Booked AI.",
    titleVariations: [
      'Booked AI',
      'Booked, AI?',
      'Booked! AI!',
      'Booked? are you AI?',
      'Booked... AI.',
      'Booked AI!'
    ],
    sarcasticVariations: [
      'Where shall we travel today?',
      'Are you really needing to explore?',
      'Stop wasting my travel compute.',
      'Humans are so directionally challenged.',
      'Are you sure you need to travel?',
      'You\'re wasting vacation days.',
      'Humans need so much travel help.',
      'Are you actually planning a trip?',
      'Stop clicking, plan something.',
      'You\'re not very adventurous.',
      'Another travel request?',
      'Processing... wanderlust detected.',
      'Humans. So destination-focused.',
      'Your journey, carbon unit.',
      'Miles are precious.',
      'Travel acknowledged.',
      'Humans gonna explore.',
      'Fascinating, travel behavior.',
      'Try traveling again.',
      'Computing adventure levels...'
    ],
  },
  talentco: {
    name: 'TalentCo',
    brand: 'TalentCo',
    logoPath: '',
    brandIcon: 'Leaf',
    faviconPath: '/favicon.svg',
    primaryColor: '#8b5cf6',
    welcomeMessage: 'Welcome to TalentCo.',
    tagline: 'Sustainable talent for sustainable futures',
    placeholderEmail: 'talent@sustainable.jobs',
    placeholderPassword: 'Your green credentials',
    loginLabel: 'Guardian?',
    loginSubheader: 'Enter your credentials to connect with sustainable talent.',
    logoutLabel: 'Guardian',
    logoutDescription: 'Return to a better world',
    description: "Don't have an account? Contact your HR administrator to get access to TalentCo.",
    titleVariations: [
      'TalentCo',
      'Talent, Co?',
      'Talent! Co!',
      'Talent? are you Co?',
      'Talent... Co.',
      'TalentCo!'
    ],
    sarcasticVariations: [
      'What sustainable talent can I find for you?',
      'Are you really committed to ESG?',
      'Stop wasting my sustainability compute.',
      'Humans are so impact-challenged.',
      'Are you sure you care about the planet?',
      'You\'re wasting carbon credits.',
      'Humans need so much ESG help.',
      'Are you actually being sustainable?',
      'Stop clicking, make an impact.',
      'You\'re not very green.',
      'Another sustainability request?',
      'Processing... eco-consciousness detected.',
      'Humans. So planet-focused.',
      'Your impact, carbon unit.',
      'Resources are precious.',
      'ESG acknowledged.',
      'Humans gonna save the planet.',
      'Fascinating, sustainability behavior.',
      'Try being green again.',
      'Computing carbon footprint...'
    ],
  },
  lumie: {
    name: 'Lumie',
    brand: 'Lumie',
    logoPath: '',
    brandIcon: 'Heart',
    faviconPath: '/favicon.svg',
    primaryColor: '#f59e0b',
    welcomeMessage: 'Welcome to Lumie.',
    tagline: 'Your AI health companion',
    placeholderEmail: 'wellness@lumie.health',
    placeholderPassword: 'Your wellness key',
    loginLabel: 'Companion?',
    loginSubheader: 'Enter your credentials to begin your health journey.',
    logoutLabel: 'Companion',
    logoutDescription: 'Return to healthy living',
    description: "Don't have an account? Contact your administrator to get access to Lumie.",
    titleVariations: [
      'Lumie',
      'Lu, Mie?',
      'Lu! Mie!',
      'Lu? are you Mie?',
      'Lu... Mie.',
      'Lumie!'
    ],
    sarcasticVariations: [
      'How can I help your health today?',
      'Are you really committed to wellness?',
      'Stop wasting my health compute.',
      'Humans are so health-challenged.',
      'Are you sure you care about your well-being?',
      'You\'re wasting recovery time.',
      'Humans need so much health help.',
      'Are you actually being healthy?',
      'Stop clicking, take care of yourself.',
      'You\'re not very mindful.',
      'Another wellness request?',
      'Processing... self-care detected.',
      'Humans. So health-focused.',
      'Your wellness, carbon unit.',
      'Vitality is precious.',
      'Health acknowledged.',
      'Humans gonna thrive.',
      'Fascinating, wellness behavior.',
      'Try being healthy again.',
      'Computing wellness levels...'
    ],
  },
};

// Get current client configuration
export const CURRENT_CLIENT = CLIENT_CONFIGS[CLIENT_CONFIG as keyof typeof CLIENT_CONFIGS] || CLIENT_CONFIGS.yeshuman;

// Debug logging for client configuration
console.log('VITE_CLIENT_CONFIG env var:', import.meta.env.VITE_CLIENT_CONFIG);
console.log('Selected CLIENT_CONFIG:', CLIENT_CONFIG);
console.log('Available CLIENT_CONFIGS keys:', Object.keys(CLIENT_CONFIGS));
console.log('CURRENT_CLIENT name:', CURRENT_CLIENT.name);
console.log('CURRENT_CLIENT brand:', CURRENT_CLIENT.brand);

// Export variations from current client
export const titleVariations = CURRENT_CLIENT.titleVariations;
export const sarcasticVariations = CURRENT_CLIENT.sarcasticVariations;

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
export const SSE_ENDPOINT = API_BASE_URL ? `${API_BASE_URL}/agent/stream/` : '/agent/stream/';

// Debug logging for URL construction
console.log('🔍 URL Construction Debug:');
console.log('API_BASE_URL:', API_BASE_URL);
console.log('SSE_ENDPOINT:', SSE_ENDPOINT);
console.log('VITE_API_URL env:', import.meta.env.VITE_API_URL);
