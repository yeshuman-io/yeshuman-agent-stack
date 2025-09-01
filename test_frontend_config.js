#!/usr/bin/env node
/**
 * Test script to verify frontend multi-tenant configuration.
 * Run with: node test_frontend_config.js
 */

// Simulate different client configurations
const CLIENT_CONFIGS = {
  yeshuman: {
    name: 'Yes Human',
    brand: 'Yes Human',
    logoPath: '/logos/yeshuman-logo.svg',
    primaryColor: '#3b82f6',
    welcomeMessage: 'Yes, welcome human.',
    tagline: 'Exploring the depths of human experience',
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
    ],
  },
  bookedai: {
    name: 'Booked AI',
    brand: 'Booked AI',
    logoPath: '/logos/bookedai-logo.svg',
    primaryColor: '#10b981',
    welcomeMessage: 'Welcome to Booked AI.',
    tagline: 'Intelligent booking and scheduling',
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
      'What can I book for you?',
      'Are you really needing to book?',
      'Stop wasting my scheduling compute.',
      'Humans are so disorganized.',
      'Are you sure you need to book?',
    ],
  },
  talentco: {
    name: 'TalentCo',
    brand: 'TalentCo',
    logoPath: '/logos/talentco-logo.svg',
    primaryColor: '#8b5cf6',
    welcomeMessage: 'Welcome to TalentCo.',
    tagline: 'Connecting talent with opportunity',
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
      'What talent can I find for you?',
      'Are you really needing talent?',
      'Stop wasting my recruitment compute.',
      'Humans are so talent-challenged.',
      'Are you sure you need talent?',
    ],
  },
  lumie: {
    name: 'Lumie',
    brand: 'Lumie',
    logoPath: '/logos/lumie-logo.svg',
    primaryColor: '#f59e0b',
    welcomeMessage: 'Welcome to Lumie.',
    tagline: 'Illuminating spaces, inspiring lives',
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
      'What light can I create for you?',
      'Are you really needing illumination?',
      'Stop wasting my lighting compute.',
      'Humans are so light-challenged.',
      'Are you sure you need light?',
    ],
  },
};

// Test different client configurations
const testConfigs = ['yeshuman', 'bookedai', 'talentco', 'lumie'];

console.log("🎨 Testing Frontend Multi-Tenant Configuration");
console.log("=" * 50);

testConfigs.forEach(client => {
  console.log(`\n📱 Testing client: ${client}`);

  // Simulate environment variable
  const CLIENT_CONFIG = process.env.VITE_CLIENT_CONFIG || client;

  // Get current client configuration
  const CURRENT_CLIENT = CLIENT_CONFIGS[CLIENT_CONFIG] || CLIENT_CONFIGS.yeshuman;

  console.log(`✅ Client: ${CLIENT_CONFIG}`);
  console.log(`🏷️  Brand: ${CURRENT_CLIENT.brand}`);
  console.log(`🎨 Primary Color: ${CURRENT_CLIENT.primaryColor}`);
  console.log(`💬 Welcome: ${CURRENT_CLIENT.welcomeMessage}`);
  console.log(`🏷️  Tagline: ${CURRENT_CLIENT.tagline}`);
  console.log(`📝 Title Variations: ${CURRENT_CLIENT.titleVariations.length} variations`);
  console.log(`😏 Sarcastic Messages: ${CURRENT_CLIENT.sarcasticVariations.length} messages`);
});

console.log("\n" + "=" * 50);
console.log("🎉 Frontend multi-tenant configuration test completed!");
console.log("\nTo switch clients in frontend:");
console.log("1. Set VITE_CLIENT_CONFIG in your .env file");
console.log("2. Restart the Vite dev server");
console.log("3. The UI will automatically update with new branding");
