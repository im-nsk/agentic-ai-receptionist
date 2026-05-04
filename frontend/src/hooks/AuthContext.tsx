import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getClient, type ClientResponse } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { getToken, isTokenExpired, logout, setToken } from '@/utils/auth';

interface AuthContextType {
  profile: Pick<ClientResponse, 'name'> | null;
  profileLoading: boolean;
  profileError: string | null;
  refreshProfile: () => Promise<void>;
  loginWithToken: (token: string) => void;
  logoutUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<Pick<ClientResponse, 'name'> | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);

  const fetchProfile = useCallback(async () => {
    const token = getToken();
    if (!token || isTokenExpired(token)) {
      setProfile(null);
      setProfileError(null);
      setProfileLoading(false);
      return;
    }

    setProfileLoading(true);
    setProfileError(null);

    try {
      const client = await getClient();
      setProfile({ name: client.name });
    } catch (e) {
      setProfile(null);
      setProfileError(getApiErrorMessage(e));
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const loginWithToken = useCallback((token: string) => {
    setToken(token);
    void fetchProfile();
  }, [fetchProfile]);

  const logoutUser = useCallback(() => {
    logout();
  }, []);

  const value = useMemo(
    () => ({
      profile,
      profileLoading,
      profileError,
      refreshProfile: fetchProfile,
      loginWithToken,
      logoutUser,
    }),
    [fetchProfile, loginWithToken, logoutUser, profile, profileLoading, profileError]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
