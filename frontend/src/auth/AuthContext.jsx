import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("fraudshield_token"));
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(token));

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      if (!token) {
        setBooting(false);
        return;
      }

      try {
        const profile = await api.me();
        if (!cancelled) setUser(profile);
      } catch {
        localStorage.removeItem("fraudshield_token");
        if (!cancelled) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setBooting(false);
      }
    }

    loadUser();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function login(email, password) {
    const response = await api.login({ email, password });
    localStorage.setItem("fraudshield_token", response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  }

  async function register(payload) {
    const response = await api.register(payload);
    localStorage.setItem("fraudshield_token", response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  }

  function logout() {
    localStorage.removeItem("fraudshield_token");
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({ token, user, booting, authenticated: Boolean(token && user), login, register, logout }),
    [token, user, booting]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

