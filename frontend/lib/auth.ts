/**
 * Authentication helper functions
 * Provides utilities for login, signup, logout, and session management
 */

import { supabase } from './supabase';
import type { User, Session } from '@supabase/supabase-js';

export interface AuthResult {
  success: boolean;
  error?: string;
  user?: User;
}

export interface SessionInfo {
  user: User | null;
  session: Session | null;
  isAuthenticated: boolean;
}

/**
 * Sign up a new user with email and password
 */
export async function signUp(email: string, password: string): Promise<AuthResult> {
  try {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/`,
      },
    });

    if (error) {
      return {
        success: false,
        error: error.message,
      };
    }

    if (data.user) {
      return {
        success: true,
        user: data.user,
      };
    }

    return {
      success: false,
      error: 'Unknown error during signup',
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to sign up',
    };
  }
}

/**
 * Sign in an existing user with email and password
 */
export async function signIn(email: string, password: string): Promise<AuthResult> {
  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      return {
        success: false,
        error: error.message,
      };
    }

    if (data.user) {
      return {
        success: true,
        user: data.user,
      };
    }

    return {
      success: false,
      error: 'Unknown error during sign in',
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to sign in',
    };
  }
}

/**
 * Sign out the current user
 */
export async function signOut(): Promise<AuthResult> {
  try {
    const { error } = await supabase.auth.signOut();

    if (error) {
      return {
        success: false,
        error: error.message,
      };
    }

    return {
      success: true,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to sign out',
    };
  }
}

/**
 * Get the current user session
 */
export async function getSession(): Promise<SessionInfo> {
  try {
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      console.error('Session error:', error);
      return {
        user: null,
        session: null,
        isAuthenticated: false,
      };
    }

    return {
      user: data.session?.user || null,
      session: data.session,
      isAuthenticated: !!data.session,
    };
  } catch (error) {
    console.error('Failed to get session:', error);
    return {
      user: null,
      session: null,
      isAuthenticated: false,
    };
  }
}

/**
 * Force refresh the current session to get a new access token
 */
export async function refreshSession(): Promise<boolean> {
  try {
    const { data, error } = await supabase.auth.refreshSession();

    if (error) {
      console.error('Failed to refresh session:', error);
      return false;
    }

    return !!data.session;
  } catch (error) {
    console.error('Failed to refresh session:', error);
    return false;
  }
}

/**
 * Get the current user's access token (JWT)
 * Automatically refreshes the token if it's expired or close to expiring
 */
export async function getAccessToken(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getSession();

    if (!data.session) {
      return null;
    }

    // Check if token is expired or expires soon (within 5 minutes)
    const expiresAt = data.session.expires_at;
    if (expiresAt) {
      const now = Math.floor(Date.now() / 1000);
      const expiresIn = expiresAt - now;

      // If token expires in less than 5 minutes, refresh it
      if (expiresIn < 300) {
        console.log('Token expires soon, refreshing...');
        const refreshed = await refreshSession();

        if (refreshed) {
          // Get the new session after refresh
          const { data: newData } = await supabase.auth.getSession();
          return newData.session?.access_token || null;
        }
      }
    }

    return data.session.access_token;
  } catch (error) {
    console.error('Failed to get access token:', error);
    return null;
  }
}

/**
 * Send a password reset email
 */
export async function resetPassword(email: string): Promise<AuthResult> {
  try {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    if (error) {
      return {
        success: false,
        error: error.message,
      };
    }

    return {
      success: true,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to send reset email',
    };
  }
}

/**
 * Update user password
 */
export async function updatePassword(newPassword: string): Promise<AuthResult> {
  try {
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    });

    if (error) {
      return {
        success: false,
        error: error.message,
      };
    }

    return {
      success: true,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update password',
    };
  }
}

/**
 * Listen for auth state changes
 */
export function onAuthStateChange(callback: (session: Session | null) => void) {
  const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session);
  });

  return subscription;
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return session.isAuthenticated;
}
