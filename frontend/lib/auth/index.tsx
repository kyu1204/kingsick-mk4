'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiClient } from '@/lib/api';

/**
 * User interface representing authenticated user data.
 */
export interface User {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

/**
 * Authentication context state and methods.
 */
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, invitationCode: string) => Promise<void>;
  refreshUser: () => Promise<void>;
}

/**
 * Login response from API.
 */
interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/**
 * Register response from API.
 */
interface RegisterResponse {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

// Token storage keys
const ACCESS_TOKEN_KEY = 'kingsick_access_token';

// Create context with default values
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Get stored access token from localStorage.
 */
function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Store access token in localStorage.
 */
function setStoredToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

/**
 * Remove access token from localStorage.
 */
function removeStoredToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

/**
 * AuthProvider component that wraps the app and provides authentication state.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  /**
   * Fetch current user from API.
   */
  const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
    const token = getStoredToken();
    if (!token) return null;

    try {
      const response = await apiClient.get<User>('/api/v1/users/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch {
      // Token is invalid or expired
      removeStoredToken();
      return null;
    }
  }, []);

  /**
   * Refresh user data from API.
   */
  const refreshUser = useCallback(async (): Promise<void> => {
    const userData = await fetchCurrentUser();
    setUser(userData);
  }, [fetchCurrentUser]);

  /**
   * Login with email and password.
   */
  const login = useCallback(async (email: string, password: string): Promise<void> => {
    const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', {
      email,
      password,
    });

    setStoredToken(response.data.access_token);
    setUser(response.data.user);
  }, []);

  /**
   * Logout and clear authentication state.
   */
  const logout = useCallback(async (): Promise<void> => {
    const token = getStoredToken();

    try {
      if (token) {
        await apiClient.post('/api/v1/auth/logout', null, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      }
    } catch {
      // Ignore logout errors
    } finally {
      removeStoredToken();
      setUser(null);
    }
  }, []);

  /**
   * Register a new user with invitation code.
   */
  const register = useCallback(async (
    email: string,
    password: string,
    invitationCode: string
  ): Promise<void> => {
    await apiClient.post<RegisterResponse>('/api/v1/auth/register', {
      email,
      password,
      invitation_code: invitationCode,
    });
  }, []);

  // Check for existing auth on mount
  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      try {
        const userData = await fetchCurrentUser();
        setUser(userData);
      } catch {
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, [fetchCurrentUser]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        logout,
        register,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Custom hook to access authentication context.
 * @throws Error if used outside of AuthProvider
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
