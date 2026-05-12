import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getClient } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { getToken, isTokenExpired, logout, setToken } from '@/utils/auth';

interface ProfileSummary {
  name: string;
  minutes_used: number;
  plan_limit: number;
  /** IANA timezone from client setup; used for booking validation in the UI. */
  timezone: string;
  /** Appointment slot length in minutes (drives booking UI + API validation). */
  slot_duration: number;
  /** Includes optional `window: { start, end }` (HH:MM) for the daily booking grid. */
  working_hours: Record<string, unknown> | string | null;
}

interface AuthContextType {
  profile: ProfileSummary | null;
  profileLoading: boolean;
  profileError: string | null;
  refreshProfile: () => Promise<void>;
  loginWithToken: (token: string) => void;
  logoutUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<ProfileSummary | null>(null);
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
      const sd = client.slot_duration;
      setProfile({
        name: client.name,
        minutes_used: client.minutes_used ?? 0,
        plan_limit: client.plan_limit ?? 0,
        timezone: (client.timezone || 'America/New_York').trim() || 'America/New_York',
        slot_duration: typeof sd === 'number' && sd > 0 ? sd : 30,
        working_hours:
          client.working_hours === null || client.working_hours === undefined
            ? null
            : (client.working_hours as Record<string, unknown> | string),
      });
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

  const loginWithToken = useCallback(
    (token: string) => {
      setToken(token);
      void fetchProfile();
    },
    [fetchProfile]
  );

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
