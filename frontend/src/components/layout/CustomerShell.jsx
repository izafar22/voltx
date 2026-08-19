import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Home, Wallet as WalletIcon, History, Bell, Moon, Sun, LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { Logo } from "@/components/Logo";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";

const nav = [
  { to: "/app", icon: Home, label: "Home" },
  { to: "/app/wallet", icon: WalletIcon, label: "Wallet" },
  { to: "/app/history", icon: History, label: "History" },
];

export const CustomerShell = ({ children }) => {
  const loc = useLocation();
  const nav_ = useNavigate();
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const [notifs, setNotifs] = useState([]);

  const load = () => api.get("/notifications").then((r) => setNotifs(r.data)).catch(() => {});
  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, [loc.pathname]);
  const unread = notifs.filter((n) => !n.read).length;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-md min-h-screen flex flex-col border-x border-border/60 relative">
        <header className="sticky top-0 z-40 glass border-b flex items-center justify-between px-5 h-14">
          <Logo />
          <div className="flex items-center gap-1">
            <button onClick={toggle} data-testid="theme-toggle" className="h-9 w-9 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200">
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <Sheet onOpenChange={(o) => { if (!o && unread) api.post("/notifications/read").then(load); }}>
              <SheetTrigger asChild>
                <button data-testid="notifications-btn" className="relative h-9 w-9 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200">
                  <Bell className="h-5 w-5" />
                  {unread > 0 && <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-charging" />}
                </button>
              </SheetTrigger>
              <SheetContent data-testid="notifications-panel">
                <SheetHeader><SheetTitle className="font-display">Notifications</SheetTitle></SheetHeader>
                <div className="mt-4 space-y-2 overflow-y-auto">
                  {notifs.length === 0 ? <p className="text-sm text-muted-foreground">No notifications yet.</p> : notifs.map((n) => (
                    <div key={n.id} className="rounded-lg border border-border/60 p-3">
                      <div className="flex items-center justify-between"><Badge variant="secondary" className="text-[10px] uppercase tracking-wider">{n.type.replace(/_/g, " ")}</Badge>{!n.read && <span className="h-1.5 w-1.5 rounded-full bg-charging" />}</div>
                      <p className="text-sm mt-1">{n.message}</p>
                      <p className="text-[11px] text-muted-foreground mt-1">{new Date(n.created_at).toLocaleString("en-IN")}</p>
                    </div>
                  ))}
                </div>
              </SheetContent>
            </Sheet>
            <button onClick={logout} data-testid="logout-btn" className="h-9 w-9 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200">
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </header>

        <main className="flex-1 pb-24">{children}</main>

        <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md glass border-t z-40">
          <div className="grid grid-cols-3 h-16">
            {nav.map((n) => {
              const active = loc.pathname === n.to;
              return (
                <Link key={n.to} to={n.to} data-testid={`nav-${n.label.toLowerCase()}`} className="flex flex-col items-center justify-center gap-0.5">
                  <n.icon className={`h-5 w-5 transition-colors duration-200 ${active ? "text-charging" : "text-muted-foreground"}`} />
                  <span className={`text-[11px] ${active ? "text-charging font-semibold" : "text-muted-foreground"}`}>{n.label}</span>
                  {active && <motion.div layoutId="tab" className="absolute bottom-0 h-0.5 w-10 bg-charging rounded-full" />}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
};
