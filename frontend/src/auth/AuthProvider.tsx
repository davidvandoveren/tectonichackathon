import { useCallback, useEffect, useState, type ReactNode } from "react";
import { getMe } from "../api/me";
import { demoLogin as demoLoginRequest, login as loginRequest, logout as logoutRequest } from "../api/auth";
import { onUnauthorized } from "../api/client";
import type { Me } from "../api/types";
import { AuthContext, type AuthStatus } from "./AuthContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<Me | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getMe(controller.signal)
      .then((me) => {
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        setUser(null);
        setStatus("unauthenticated");
      });
    return () => controller.abort();
  }, []);

  useEffect(
    () =>
      onUnauthorized(() => {
        setUser(null);
        setStatus("unauthenticated");
      }),
    []
  );

  const login = useCallback(async (username: string, password: string) => {
    const me = await loginRequest(username, password);
    setUser(me);
    setStatus("authenticated");
    return me;
  }, []);

  const demoLogin = useCallback(async (username: string) => {
    const me = await demoLoginRequest(username);
    setUser(me);
    setStatus("authenticated");
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Still sign out locally: the session cookie expires on its own on the server.
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  return <AuthContext.Provider value={{ status, user, login, demoLogin, logout }}>{children}</AuthContext.Provider>;
}
