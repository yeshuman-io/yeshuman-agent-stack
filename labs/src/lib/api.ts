
// Global reference to auth functions (set when authorizedFetch is first called)
let authLogout: (() => void) | null = null;
let authPromptLogin: (() => void) | null = null;

/**
 * Authorized fetch wrapper that handles authentication headers and 401 responses
 */
export async function authorizedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  // Get auth context (this needs to be called within a React component)
  // We'll set up the global references when this is first called
  if (!authLogout || !authPromptLogin) {
    throw new Error('authorizedFetch must be used within an AuthProvider context');
  }

  const token = localStorage.getItem('auth_token');

  // Add authorization header if token exists
  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  headers.set('Content-Type', 'application/json');

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized responses
  if (response.status === 401) {
    console.log('Received 401 response, clearing auth state and redirecting to login');
    authLogout?.();
    // Redirect to login page if not already there
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
  }

  return response;
}

/**
 * Initialize authorizedFetch with auth context functions
 * This should be called once when the app starts, within the AuthProvider
 */
export function initializeAuthorizedFetch(logout: () => void, promptLogin: () => void) {
  authLogout = logout;
  authPromptLogin = promptLogin;
}
