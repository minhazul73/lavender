import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { UserProfile, LoginResponse, ElevationResponse } from '../api/types';
import { api, registerElevationHandler, unregisterElevationHandler } from '../api/client';
import { REQUIRE_AUTH_FOR_HOMEPAGE } from '../config';

interface AuthContextValue {
  session: UserProfile | null;
  loading: boolean;
  isElevated: boolean;
  requireAuthForHomepage: boolean;
  login: (username: string, password: string, next?: string) => Promise<LoginResponse>;
  logout: (redirectTo?: string) => Promise<void>;
  elevate: (password: string) => Promise<boolean>;
  dropElevation: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  isElevationModalOpen: boolean;
  openElevationModal: () => Promise<boolean>;
  closeElevationModal: (success?: boolean) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [requireAuthForHomepage, setRequireAuthForHomepage] = useState<boolean>(REQUIRE_AUTH_FOR_HOMEPAGE);
  const [isElevationModalOpen, setIsElevationModalOpen] = useState(false);
  const elevationResolverRef = useRef<((value: boolean) => void) | null>(null);

  const refreshProfile = useCallback(async () => {
    try {
      const profile = await api.get<UserProfile>('/auth/me', { timeoutMs: 6000 });
      setSession(profile);
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  useEffect(() => {
    api.get<{ require_auth_for_homepage?: boolean }>('/auth/config')
      .then((cfg) => {
        if (cfg && typeof cfg.require_auth_for_homepage === 'boolean') {
          setRequireAuthForHomepage(cfg.require_auth_for_homepage);
        }
      })
      .catch(() => {});
  }, []);

  const openElevationModal = useCallback((): Promise<boolean> => {
    setIsElevationModalOpen(true);
    return new Promise<boolean>((resolve) => {
      elevationResolverRef.current = resolve;
    });
  }, []);

  const closeElevationModal = useCallback((success = false) => {
    setIsElevationModalOpen(false);
    if (elevationResolverRef.current) {
      elevationResolverRef.current(success);
      elevationResolverRef.current = null;
    }
  }, []);

  useEffect(() => {
    registerElevationHandler(openElevationModal);
    return () => {
      unregisterElevationHandler();
    };
  }, [openElevationModal]);

  const login = async (username: string, password: string, next = '/'): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>('/auth/login', { username, password, next });
    if (res.success) {
      await refreshProfile();
    }
    return res;
  };

  const logout = async (redirectTo?: string): Promise<void> => {
    try {
      await api.post('/auth/logout');
    } finally {
      setSession(null);
      if (redirectTo) {
        window.location.href = redirectTo;
        return;
      }
      const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';
      const isPublicHome = !requireAuthForHomepage && (currentPath === '/' || currentPath === '');
      if (!isPublicHome) {
        window.location.href = '/login';
      }
    }
  };

  const elevate = async (password: string): Promise<boolean> => {
    try {
      const res = await api.post<ElevationResponse>('/auth/elevate', { password });
      if (res.success) {
        await refreshProfile();
        closeElevationModal(true);
        return true;
      }
      return false;
    } catch (err) {
      throw err;
    }
  };

  const dropElevation = async (): Promise<void> => {
    try {
      await api.post('/auth/drop-admin');
      await refreshProfile();
    } catch (err) {
      console.error('Failed to drop elevation:', err);
    }
  };

  const isElevated = Boolean(session?.is_admin);

  return (
    <AuthContext.Provider
      value={{
        session,
        loading,
        isElevated,
        requireAuthForHomepage,
        login,
        logout,
        elevate,
        dropElevation,
        refreshProfile,
        isElevationModalOpen,
        openElevationModal,
        closeElevationModal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export { AuthContext };

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function useOptionalAuth() {
  return useContext(AuthContext);
}
