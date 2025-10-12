/**
 * JWT utility functions for decoding and validating tokens
 */

export interface JwtPayload {
  user_id: number;
  username: string;
  email: string;
  exp: number;
  iat: number;
  [key: string]: any;
}

/**
 * Decode JWT payload without verification
 */
export function getJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format');
    }

    // Decode payload (second part)
    const payload = parts[1];

    // Convert base64url to base64
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');

    // Add padding if needed
    const paddedBase64 = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');

    // Decode and parse
    const decoded = atob(paddedBase64);
    return JSON.parse(decoded);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

/**
 * Check if JWT token is expired
 * @param token - JWT token string
 * @param skewSeconds - Number of seconds to subtract from expiry for safety margin (default: 30)
 */
export function isJwtExpired(token: string, skewSeconds: number = 30): boolean {
  const payload = getJwtPayload(token);
  if (!payload || !payload.exp) {
    return true; // Consider invalid/missing tokens as expired
  }

  const now = Math.floor(Date.now() / 1000); // Current time in seconds
  const expiryTime = payload.exp - skewSeconds; // Apply skew

  return now >= expiryTime;
}

/**
 * Get remaining seconds until token expires
 */
export function getJwtExpirySeconds(token: string): number {
  const payload = getJwtPayload(token);
  if (!payload || !payload.exp) {
    return 0;
  }

  const now = Math.floor(Date.now() / 1000);
  return Math.max(0, payload.exp - now);
}
