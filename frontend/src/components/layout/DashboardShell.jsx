import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LogOut, Menu, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { PublicSiteLink } from "./SidebarLinks";
import { ThemeToggle } from "../ThemeToggle";
import { Logo } from "@/components/Logo";

export const DashboardShell = ({ children, nav, title }) => {
  const loc = useLocation();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const SideNav = () => (
    <nav className="flex flex-col gap-1 p-3">
      {nav.map((n) => {
        const active = n.active !== undefined ? n.active : loc.pathname === n.to;
        const cls = `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-200 ${active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"}`;
        const testid = `side-${n.label.toLowerCase().replace(/\s/g, "-")}`;
        if (n.onClick) return (
          <button key={n.label} onClick={() => { n.onClick(); setOpen(false); }} data-testid={testid} className={cls + " text-left w-full"}>
            <n.icon className="h-4.5 w-4.5" strokeWidth={1.5} /> {n.label}
          </button>
        );
        return (
          <Link key={n.to} to={n.to} onClick={() => setOpen(false)} data-testid={testid} className={cls}>
            <n.icon className="h-4.5 w-4.5" strokeWidth={1.5} /> {n.label}
          </Link>
        );
      })}
      <PublicSiteLink onClick={() => setOpen(false)} />
    </nav>
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-border/60 sticky top-0 h-screen">
        <div className="h-16 flex items-center px-5 border-b border-border/60"><Logo /></div>
        <div className="flex-1 overflow-y-auto"><SideNav /></div>
        <div className="p-3 border-t border-border/60">
          <div className="px-3 py-2 text-sm"><p className="font-medium truncate">{user?.name}</p><p className="text-xs text-muted-foreground">{user?.role}</p></div>
        </div>
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="w-64 bg-background border-r border-border/60 flex flex-col" data-testid="mobile-drawer">
            <div className="h-16 flex items-center justify-between px-5 border-b border-border/60"><Logo /><button onClick={() => setOpen(false)}><X className="h-5 w-5" /></button></div>
            <SideNav />
          </div>
          <div className="flex-1 bg-black/40" onClick={() => setOpen(false)} />
        </div>
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-40 glass border-b h-16 flex items-center justify-between px-4 lg:px-8">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" onClick={() => setOpen(true)} data-testid="menu-btn"><Menu className="h-6 w-6" /></button>
            <h1 className="font-display text-lg font-semibold">{title}</h1>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button onClick={logout} data-testid="logout-btn" className="h-9 w-9 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200"><LogOut className="h-5 w-5" /></button>
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
};
