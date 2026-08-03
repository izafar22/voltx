import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, ShieldCheck, LayoutDashboard, Wrench } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export default function Login() {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => { if (user) navigate("/portal"); }, [user, navigate]);

  const handleGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/portal";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] grid lg:grid-cols-2" data-testid="login-page">
      <div className="hidden lg:flex flex-col justify-between bg-slate-950 text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 grain opacity-20" />
        <div className="relative flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center"><Zap className="h-5 w-5 text-white" fill="white" /></div>
          <span className="font-display font-extrabold text-xl">RUSHX</span>
        </div>
        <div className="relative">
          <h2 className="font-display text-4xl font-extrabold leading-tight">Your energy, <br />under control.</h2>
          <p className="mt-4 text-slate-300 max-w-sm">Manage AMC plans, book service visits and track your quotes — all in one premium portal.</p>
          <div className="mt-8 space-y-4">
            {[{ icon: LayoutDashboard, t: "Unified dashboard" }, { icon: Wrench, t: "Book service in seconds" }, { icon: ShieldCheck, t: "AMC plans & invoices" }].map((f) => (
              <div key={f.t} className="flex items-center gap-3"><div className="h-10 w-10 rounded-lg bg-white/10 flex items-center justify-center"><f.icon className="h-5 w-5 text-emerald-400" /></div><span>{f.t}</span></div>
            ))}
          </div>
        </div>
        <div className="relative text-sm text-slate-500">© {new Date().getFullYear()} RUSHX Energy Solutions</div>
      </div>

      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-sm text-center">
          <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
            <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center"><Zap className="h-5 w-5 text-white" fill="white" /></div>
            <span className="font-display font-extrabold text-xl">RUSHX</span>
          </div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight">Welcome back</h1>
          <p className="mt-2 text-muted-foreground">Sign in to access your customer portal.</p>
          <Button onClick={handleGoogle} data-testid="google-login-btn" size="lg" variant="outline" className="mt-8 w-full h-13 rounded-lg gap-3 text-base">
            <svg className="h-5 w-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
          </Button>
          <p className="mt-6 text-xs text-muted-foreground">By signing in you agree to RUSHX's terms of service and privacy policy.</p>
        </div>
      </div>
    </div>
  );
}
