import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Home, Wallet as WalletIcon, History, Wrench, Bell, LogOut, Menu, LayoutDashboard, Shield } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ThemeToggle } from "../ThemeToggle";
import { Logo } from "@/components/Logo";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";

import { FEATURES } from "../../config/features";

const nav = [
  { to: "/app", icon: Home, label: "Home" },
  { to: "/app/wallet", icon: WalletIcon, enabled: () => FEATURES.wallet, label: "Wallet" },
  { to: "/app/history", icon: History, enabled: () => FEATURES.charging, label: "History" },
  { to: "/repairs", icon: Wrench, enabled: () => FEATURES.repair, label: "Repairs" },
];

export const CustomerShell = ({ children }) => {
  const loc = useLocation();
  const navigate = useNavigate();
  const { user, logout, loggingOut, authError } = useAuth();
  const [notifs, setNotifs] = useState([]);
  const [open, setOpen] = useState(false);

  // Existing notifications are exclusively charging/wallet events.
  const showNotifications = FEATURES.charging || FEATURES.wallet;
  const load = () => api.get("/notifications").then((r) => setNotifs(r.data)).catch(() => {});
  useEffect(() => { if (!showNotifications) return; load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, [loc.pathname, showNotifications]);
  const unread = notifs.filter((n) => !n.read).length;

  const SideNav = () => (
    <nav aria-label="Customer navigation" className="flex flex-col gap-1 p-3">
      {nav.filter((n) => !n.enabled || n.enabled()).map((n) => {
        const active = loc.pathname === n.to || (n.to === "/repairs" && loc.pathname.startsWith("/repairs/"));
        return (
          <Link key={n.to} to={n.to} onClick={() => setOpen(false)} data-testid={`nav-${n.label.toLowerCase()}`} aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring ${active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"}`}>
            <n.icon className="h-4.5 w-4.5" strokeWidth={1.5} /> {n.label}
          </Link>
        );
      })}
      {(user?.role === "owner" || user?.role === "admin") && (
        <button onClick={() => navigate(user.role === "admin" ? "/admin" : "/owner")} data-testid="nav-console"
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-secondary/60 hover:text-foreground transition-colors duration-200 mt-2">
          {user.role === "admin" ? <Shield className="h-4.5 w-4.5" strokeWidth={1.5} /> : <LayoutDashboard className="h-4.5 w-4.5" strokeWidth={1.5} />}
          {user.role === "admin" ? "Admin Console" : "Owner Console"}
        </button>
      )}
    </nav>
  );

  return (
    <div className="customer-shell min-h-screen bg-background flex">
      <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-border/60 sticky top-0 h-screen">
        <div className="h-16 flex items-center px-5 border-b border-border/60"><Logo /></div>
        <div className="flex-1 overflow-y-auto"><SideNav /></div>
        <div className="p-3 border-t border-border/60"><div className="px-3 py-2 text-sm"><p className="font-medium truncate">{user?.name}</p><p className="text-xs text-muted-foreground font-mono">{user?.phone}</p></div></div>
      </aside>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="w-64 p-0" data-testid="mobile-drawer" aria-describedby={undefined}>
          <SheetHeader className="p-5"><SheetTitle><Logo /></SheetTitle></SheetHeader>
          <SideNav />
        </SheetContent>
      </Sheet>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-40 glass border-b h-16 flex items-center justify-between px-4 lg:px-8">
          <div className="flex items-center gap-3">
            <button className="lg:hidden h-11 w-11 flex items-center justify-center" onClick={() => setOpen(true)} data-testid="menu-btn" aria-label="Open navigation" aria-expanded={open}><Menu className="h-6 w-6" /></button>
            <div className="lg:hidden"><Logo compact /></div>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            {showNotifications && <Sheet onOpenChange={(o) => { if (!o && unread) api.post("/notifications/read").then(load).catch(() => {}); }}>
              <SheetTrigger asChild>
                <button data-testid="notifications-btn" aria-label="Notifications" className="relative h-11 w-11 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200">
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
            </Sheet>}
            <form onSubmit={(event) => { event.preventDefault(); logout(); }}><button type="submit" disabled={loggingOut} data-testid="logout-btn" aria-label={loggingOut ? "Signing out" : "Log out"} className="h-11 w-11 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200"><LogOut className="h-5 w-5" /></button></form>
          </div>
        </header>
        <main className="flex-1">{authError && <p role="alert" className="p-4 text-sm text-destructive">{authError}</p>}{children}</main>
      </div>
    </div>
  );
};
