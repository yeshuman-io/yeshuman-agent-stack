import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { API_BASE_URL } from '@/constants';
import { isJwtExpired } from '@/utils/jwt';
import { initializeAuthorizedFetch } from '@/lib/api';

// Helper to check if we're on the login page
const isOnLoginPage = () => window.location.pathname.startsWith('/login');

interface User {
  id: number;
  username: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  isAuthenticated: boolean;
  refreshThreads: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Use the configured API base URL, fallback to relative path for same-domain requests
const API_URL = API_BASE_URL || '/api';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load auth state from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');

    if (storedToken && storedUser) {
      try {
        // Check if token is expired before setting it
        if (isJwtExpired(storedToken)) {
          console.log('Stored token is expired, clearing auth state and redirecting to login');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('auth_user');
          if (!isOnLoginPage()) {
            window.location.href = '/login';
          }
        } else {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error('Failed to parse stored auth data:', error);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        if (!isOnLoginPage()) {
          window.location.href = '/login';
        }
      }
    } else {
      // Only redirect to login if we're not already there
      if (!isOnLoginPage()) {
        window.location.href = '/login';
      }
    }
  }, []);

  // Check token expiry periodically
  useEffect(() => {
    const checkTokenExpiry = () => {
      if (token && isJwtExpired(token)) {
        console.log('Token expired during session, clearing auth state and redirecting to login');
        logout();
        if (!isOnLoginPage()) {
          window.location.href = '/login';
        }
      }
    };

    // Check every 60 seconds
    const interval = setInterval(checkTokenExpiry, 60000);

    return () => clearInterval(interval);
  }, [token]);

  // Initialize authorizedFetch with auth functions
  useEffect(() => {
    // Create a no-op promptLogin since we removed that functionality
    const promptLogin = () => {
      if (!isOnLoginPage()) {
        window.location.href = '/login';
      }
    };
    initializeAuthorizedFetch(logout, promptLogin);
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/accounts/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: email, password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setUser(data.user);
        setToken(data.token);

        // Store in localStorage
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('auth_user', JSON.stringify(data.user));

        return { success: true };
      } else {
        return { success: false, error: data.error || 'Login failed' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Network error. Please try again.' };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
  };

  const refreshThreads = () => {
    // This function can be implemented to refresh threads
    // For now, it's a placeholder to satisfy the interface
    console.log('Refresh threads called');
  };

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    login,
    logout,
    isAuthenticated: !!user && !!token,
    refreshThreads,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
