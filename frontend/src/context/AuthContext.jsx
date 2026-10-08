import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const AuthContext = createContext();
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);
  const logoutLock = useRef(false);
  const [authError, setAuthError] = useState("");
  const queryClient = useQueryClient();
  const generation = useRef(0);
  const loadMe = useCallback(async () => {
    const requestGeneration = ++generation.current;
    setLoading(true); setAuthError("");
    // Migration only: browser code never reads or writes session JWTs.
    localStorage.removeItem("ev_token");
    try { const { data } = await api.get("/auth/me"); if (requestGeneration === generation.current) setUser(data); }
    catch (error) {
      if (requestGeneration !== generation.current) return;
      setUser(null);
      if (![401, 403].includes(error.response?.status)) setAuthError("Unable to check your session. Please try again.");
    } finally { if (requestGeneration === generation.current) setLoading(false); }
  }, []);
  useEffect(() => { loadMe(); return () => { generation.current += 1; }; }, [loadMe]);
  const login = (profile) => { generation.current += 1; setLoading(false); queryClient.clear(); setAuthError(""); setUser(profile); };
  const logout = async () => {
    if (logoutLock.current) return;
    logoutLock.current = true; setLoggingOut(true);
    try {
      await api.post("/auth/logout");
      generation.current += 1; queryClient.clear(); localStorage.removeItem("ev_token"); setUser(null); setAuthError("");
    } catch { setAuthError("Unable to sign out. Please try again."); }
    finally { logoutLock.current = false; setLoggingOut(false); }
  };
  return <AuthContext.Provider value={{ user, setUser, loading, login, logout, loggingOut, authError, loadMe }}>{children}</AuthContext.Provider>;
};
export const useAuth = () => useContext(AuthContext);
