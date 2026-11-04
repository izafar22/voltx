import { Link, useLocation } from "react-router-dom";
import { Globe } from "lucide-react";
export function PublicSiteLink({ onClick }) {
  return (
    <Link
      to="/"
      onClick={onClick}
      className="min-h-11 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
    >
      <Globe aria-hidden="true" className="h-4 w-4" />
      Explore RushX
    </Link>
  );
}
export function SidebarLinks({ items, onNavigate, children }) {
  const { pathname } = useLocation();
  return (
    <nav aria-label="Customer navigation" className="flex flex-col gap-1 p-3">
      {items.map(({ to, label, icon: Icon }) => {
        const active =
          pathname === to ||
          (to === "/repairs" && pathname.startsWith("/repairs/"));
        return (
          <Link
            key={to}
            to={to}
            onClick={onNavigate}
            data-testid={`nav-${label.toLowerCase()}`}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 min-h-11 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring ${active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"}`}
          >
            <Icon aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
            {label}
          </Link>
        );
      })}
      {children}
      <PublicSiteLink onClick={onNavigate} />
    </nav>
  );
}
