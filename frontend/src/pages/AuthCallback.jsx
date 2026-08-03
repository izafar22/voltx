import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const sessionId = new URLSearchParams(hash.replace("#", "")).get("session_id");
    if (!sessionId) { navigate("/login"); return; }

    (async () => {
      try {
        const { data } = await api.post("/auth/session", null, { headers: { "X-Session-ID": sessionId } });
        setUser(data);
        window.history.replaceState(null, "", window.location.pathname);
        navigate(data.role === "admin" ? "/admin" : "/portal", { state: { user: data } });
      } catch {
        navigate("/login");
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center gap-4" data-testid="auth-callback">
      <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center animate-pulse"><Zap className="h-6 w-6 text-white" fill="white" /></div>
      <div className="flex items-center gap-2 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Signing you in...</div>
    </div>
  );
}
