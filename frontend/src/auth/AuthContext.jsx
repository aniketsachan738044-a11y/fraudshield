import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      try {
        const profile = await api.me();
        if (!cancelled) setUser(profile);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setBooting(false);
      }
    }

    loadUser();
    return () => {
      cancelled = true;
    };
  }, []);

  async function login(email, password) {
    const response = await api.login({ email, password });
    if (response.access_token) {
      localStorage.setItem("fraudshield_token", response.access_token);
    }
    setUser(response.user);
  }

  async function register(payload) {
    const response = await api.register(payload);
    if (response.access_token) {
      localStorage.setItem("fraudshield_token", response.access_token);
    }
    setUser(response.user);
  }

  async function logout() {
    try {
      await api.logout();
    } finally {
      localStorage.removeItem("fraudshield_token");
      setUser(null);
    }
  }

  const value = useMemo(
    () => ({ user, booting, authenticated: Boolean(user), login, register, logout }),
    [user, booting]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
