import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Zap, Moon, Sun, Menu, X, LayoutDashboard, LogOut, Shield, ArrowUpRight } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

const links = [
  { to: "/products", label: "Products" },
  { to: "/services", label: "Services" },
  { to: "/why-rushx", label: "Why RUSHX" },
  { to: "/segments", label: "Segments" },
  { to: "/contact", label: "Contact" },
];

export const Navbar = () => {
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const nav = useNavigate();

  return (
    <header className="sticky top-0 z-50 glass" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-5 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2" data-testid="nav-logo">
          <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
            <Zap className="h-5 w-5 text-white" fill="white" />
          </div>
          <span className="font-display font-extrabold text-xl tracking-tight">RUSHX</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-1">
          {links.map((l) => (
            <Link key={l.to} to={l.to} data-testid={`nav-${l.label.toLowerCase().replace(/\s/g, "-")}`}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 hover:text-primary ${loc.pathname === l.to ? "text-primary" : "text-muted-foreground"}`}>
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button onClick={toggle} data-testid="theme-toggle"
            className="h-10 w-10 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200">
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
          {user ? (
            <div className="hidden sm:flex items-center gap-2">
              {user.role === "admin" && (
                <Button variant="outline" size="sm" onClick={() => nav("/admin")} data-testid="nav-admin-btn">
                  <Shield className="h-4 w-4 mr-1" /> Admin
                </Button>
              )}
              <Button size="sm" onClick={() => nav("/portal")} data-testid="nav-portal-btn" className="rounded-lg">
                <LayoutDashboard className="h-4 w-4 mr-1" /> Portal
              </Button>
              <button onClick={logout} data-testid="nav-logout-btn" className="h-10 w-10 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors duration-200">
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          ) : (
            <Button variant="repairCta" size="sm" onClick={() => nav("/login")} data-testid="nav-login-btn" className="hidden sm:inline-flex rounded-lg">
              <Zap aria-hidden="true" /> Book a Repair <ArrowUpRight aria-hidden="true" />
            </Button>
          )}
          <button onClick={() => setOpen(!open)} data-testid="nav-mobile-toggle" className="lg:hidden h-10 w-10 rounded-lg flex items-center justify-center hover:bg-secondary">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="lg:hidden border-t border-border bg-background px-5 py-4 space-y-1" data-testid="mobile-menu">
          {links.map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)} className="block px-3 py-2.5 rounded-lg hover:bg-secondary font-medium">
              {l.label}
            </Link>
          ))}
          <div className="pt-2 flex gap-2">
            {user ? (
              <>
                <Button className="flex-1" onClick={() => { nav("/portal"); setOpen(false); }}>Portal</Button>
                {user.role === "admin" && <Button variant="outline" className="flex-1" onClick={() => { nav("/admin"); setOpen(false); }}>Admin</Button>}
              </>
            ) : (
              <Button variant="repairCta" onClick={() => { nav("/login"); setOpen(false); }} className="flex-1"><Zap aria-hidden="true" /> Book a Repair <ArrowUpRight aria-hidden="true" /></Button>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
