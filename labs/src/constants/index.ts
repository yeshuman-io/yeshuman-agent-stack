// Unified client configuration variable
// Note: VITE_CLIENT_CONFIG is used for frontend build-time config
// CLIENT_CONFIG is used for backend runtime config
const CLIENT_CONFIG = import.meta.env.VITE_CLIENT_CONFIG || 'yeshuman';

// API configuration for backend connection
// VITE_API_URL: Set to backend URL for cross-domain requests (optional)
// Leave empty for same-domain requests (recommended for production)
// Example: https://your-backend-api.com
export const API_BASE_URL = (import.meta.env.VITE_API_URL || '').trim();

// Import UI-specific client configurations
import uiConfig from '../../client-config.json';

// Use UI-specific configuration with all frontend fields
export const CLIENT_CONFIGS = uiConfig.clients;

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
console.log('window.location.origin:', window.location.origin);
console.log('VITE_API_URL raw:', import.meta.env.VITE_API_URL);
console.log('VITE_API_URL trimmed:', (import.meta.env.VITE_API_URL || '').trim());
console.log('API_BASE_URL:', API_BASE_URL);
console.log('API_BASE_URL type:', typeof API_BASE_URL);
console.log('API_BASE_URL length:', API_BASE_URL.length);
console.log('SSE_ENDPOINT:', SSE_ENDPOINT);
console.log('SSE_ENDPOINT type:', typeof SSE_ENDPOINT);
console.log('SSE_ENDPOINT length:', SSE_ENDPOINT.length);
console.log('SSE_ENDPOINT starts with http:', SSE_ENDPOINT.startsWith('http'));
console.log('VITE_API_URL env type:', typeof import.meta.env.VITE_API_URL);

// Check for URL construction issues
if (SSE_ENDPOINT.includes('=')) {
  console.error('❌ SSE_ENDPOINT contains = character:', SSE_ENDPOINT);
}
if (SSE_ENDPOINT.includes(window.location.origin)) {
  console.error('❌ SSE_ENDPOINT contains current origin:', SSE_ENDPOINT);
}
