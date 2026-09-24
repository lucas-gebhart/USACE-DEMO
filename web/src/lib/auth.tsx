import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, token, type DevUser } from "./api";

interface AuthState {
  user: DevUser | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DevUser | null>(null);
  const [ready, setReady] = useState(() => !token.get());
  const qc = useQueryClient();

  useEffect(() => {
    if (ready) return;
    api
      .me()
      .then(setUser)
      .catch(() => token.clear())
      .finally(() => setReady(true));
  }, [ready]);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await api.login(username, password);
      token.set(res.access_token);
      qc.clear();
      setUser(res.user);
    },
    [qc],
  );

  const logout = useCallback(() => {
    token.clear();
    qc.clear();
    setUser(null);
  }, [qc]);

  const value = useMemo(() => ({ user, ready, login, logout }), [user, ready, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
