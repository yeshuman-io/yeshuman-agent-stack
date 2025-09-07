// Type definitions for shared configuration
export interface ClientConfig {
  name: string;
  brand: string;
  logoPath: string;
  brandIcon: string;
  faviconPath: string;
  primaryColor: string;
  systemPrompt: string;
  welcomeMessage: string;
  tagline: string;
  placeholderEmail: string;
  placeholderPassword: string;
  loginLabel: string;
  loginSubheader: string;
  logoutLabel: string;
  logoutDescription: string;
  description: string;
  titleVariations: string[];
  sarcasticVariations: string[];
}

export interface SharedConfig {
  clients: Record<string, ClientConfig>;
}

export type ClientKey = keyof SharedConfig['clients'];
