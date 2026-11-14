import { Link } from "react-router-dom";
import { Logo } from "../Logo";
import { ThemeToggle } from "../ThemeToggle";

// Presentation only: all authentication state and provider actions stay in Login.
export function LoginLayout({ children, repairMode = true }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background text-foreground">
      <aside
        className="hidden lg:flex flex-col justify-between bg-secondary border-r border-border p-12"
        aria-label="About RushX"
      >
        <Link to="/" aria-label="RushX home">
          <Logo />
        </Link>
        <div>
          {repairMode ? (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                Independent, multi-brand repair enquiries
              </p>
              <h2 className="font-display text-5xl font-medium leading-tight">
                Repair when possible.
                <br />
                <span className="text-[hsl(var(--brand-foreground))]">
                  Replace when necessary.
                </span>
              </h2>
              <p className="mt-5 text-muted-foreground max-w-sm">
                Start with an assessment of your charger. Repair feasibility
                depends on the model, fault, parts and safe testing options.
              </p>
            </>
          ) : (
            <>
              <h2 className="font-display text-5xl">
                Charge as fast as you pay.
              </h2>
              <p className="mt-5 text-muted-foreground">
                Find your next charge and manage your charging.
              </p>
            </>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          RushX · EVChargerRepair.in
        </p>
      </aside>
      <div className="relative flex flex-col min-w-0">
        <nav
          aria-label="Login navigation"
          className="flex justify-between items-center gap-3 px-6 py-4 border-b border-border"
        >
          <Link
            to="/"
            className="inline-flex min-h-11 items-center text-sm underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          >
            Explore RushX
          </Link>
          <ThemeToggle />
        </nav>
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-sm space-y-6">
            <Link
              to="/"
              aria-label="RushX home"
              className="inline-block lg:hidden"
            >
              <Logo />
            </Link>
            <p className="lg:hidden text-sm text-muted-foreground">
              Repair when possible. Replace when necessary.
            </p>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
