import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(user ? "ok" : null);

  useEffect(() => {
    if (user) { setStatus(adminOnly && user.role !== "admin" ? "denied" : "ok"); return; }
    (async () => {
      try {
        const { data } = await api.get("/auth/me");
        setUser(data);
        setStatus(adminOnly && data.role !== "admin" ? "denied" : "ok");
      } catch {
        setStatus("no");
        navigate("/login");
      }
    })();
  }, [user, adminOnly, navigate, setUser]);

  if (status === "denied") {
    return <div className="min-h-[60vh] flex items-center justify-center text-muted-foreground">Admin access required.</div>;
  }
  if (status !== "ok") {
    return <div className="min-h-[60vh] flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }
  return children;
};
