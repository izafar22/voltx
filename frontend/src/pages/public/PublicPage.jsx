import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ArrowUpRight, Zap, Menu, X } from "lucide-react";
import {
  HomeStory,
  ServicesStory,
  JourneyStory,
  AboutStory,
  RepairLink,
} from "./storytelling/StoryPages";
import { ThemeToggle } from "../../components/ThemeToggle";
import { Button } from "../../components/ui/button";
import { Logo } from "../../components/Logo";
import { useAuth } from "../../context/AuthContext";
import { homeFor } from "../../components/ProtectedRoute";
import { FAQ } from "../../components/patterns/RepairPatterns";
import { faqs } from "./content";
import "./PublicPage.css";
const nav = [
  ["/services", "Services"],
  ["/how-it-works", "How it works"],
  ["/about", "About"],
  ["/faq", "FAQ"],
];
const meta = {
  "/": [
    "EV charger repair, thoughtfully assessed",
    "Independent, multi-brand EV charger repair enquiries. Explore RushX services in Delhi NCR, Mumbai and eligible courier-based enquiries across India.",
  ],
  "/services": [
    "EV charger repair services",
    "Explore PCB, AC charger, DC fast charger and power-electronics repair enquiries, including symptoms and technical eligibility.",
  ],
  "/how-it-works": [
    "How the repair process works",
    "From your first enquiry to technical acceptance, quotation, approved repair, testing and return: understand the RushX repair process.",
  ],
  "/about": [
    "About our repair-first mission",
    "Meet RushX, an independent multi-brand EV charger repair enquiry and electronics service. Repair when possible. Replace when necessary.",
  ],
  "/faq": [
    "Repair questions, answered",
    "Learn about RushX repair eligibility, coverage, courier enquiries, quotations and service terms before requesting an assessment.",
  ],
};
export default function PublicPage() {
  const { pathname, hash } = useLocation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const main = useRef(null);
  const previous = useRef(pathname);
  useEffect(() => {
    const [title, description] = meta[pathname];
    document.title = `${title} | RushX`;
    const managed = [];
    const set = (tag, attr, key, content) => {
      let el = document.head.querySelector(`${tag}[${attr}="${key}"]`);
      const created = !el;
      const old = el?.getAttribute(tag === "link" ? "href" : "content");
      if (!el) {
        el = document.createElement(tag);
        el.setAttribute(attr, key);
        document.head.appendChild(el);
      }
      el.setAttribute(tag === "link" ? "href" : "content", content);
      managed.push(() =>
        created
          ? el.remove()
          : el.setAttribute(tag === "link" ? "href" : "content", old || ""),
      );
    };
    const canonical = `https://evchargerrepair.in${pathname === "/" ? "/" : pathname}`;
    set("meta", "name", "description", description);
    set("link", "rel", "canonical", canonical);
    Object.entries({
      "og:title": `${title} | RushX`,
      "og:description": description,
      "og:url": canonical,
      "og:type": "website",
      "og:site_name": "RushX",
    }).forEach(([key, value]) => set("meta", "property", key, value));
    return () => {
      managed.forEach((clean) => clean());
      document.title = "RushX";
    };
  }, [pathname]);
  useEffect(() => {
    setOpen(false);
    if (hash) {
      document.getElementById(hash.slice(1))?.scrollIntoView();
    } else {
      window.scrollTo(0, 0);
    }
    if (previous.current !== pathname)
      main.current?.focus({ preventScroll: true });
    previous.current = pathname;
  }, [pathname, hash]);
  return (
    <div className="rx-public">
      <a className="rx-skip" href="#public-main">
        Skip to content
      </a>
      <header
        className="rx-header"
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setOpen(false);
            document.querySelector(".rx-menu-toggle")?.focus();
          }
        }}
      >
        <div className="rx-header-inner">
          <Link to="/" aria-label="RushX home">
            <Logo />
          </Link>
          <div className="rx-header-actions">
            <ThemeToggle />
            <button
              className="rx-menu-toggle"
              aria-label={open ? "Close menu" : "Open menu"}
              aria-expanded={open}
              aria-controls="public-navigation"
              onClick={() => setOpen(!open)}
            >
              {open ? <X /> : <Menu />}
            </button>
          </div>
          <nav
            id="public-navigation"
            aria-label="Main navigation"
            className={open ? "is-open" : ""}
          >
            {nav.map(([to, label]) => (
              <NavLink key={to} to={to} onClick={() => setOpen(false)}>
                {label}
              </NavLink>
            ))}
            <Link to="/repairs" onClick={() => setOpen(false)}>
              Track a repair
            </Link>
            {user ? (
              <Link className="rx-account" to={homeFor(user.role)} onClick={() => setOpen(false)}>
                My account <ArrowUpRight size={15} aria-hidden="true" />
              </Link>
            ) : (
              <Button asChild variant="repairCta" size="sm" className="rx-account-cta min-h-12 px-5">
                <Link to="/login" onClick={() => setOpen(false)}>
                  <Zap size={17} aria-hidden="true" /> Book a Repair <ArrowUpRight size={16} aria-hidden="true" />
                </Link>
              </Button>
            )}
          </nav>
        </div>
      </header>
      <main id="public-main" tabIndex={-1} ref={main}>
        {pathname === "/" && <HomeStory />}
        {pathname === "/services" && <ServicesStory />}
        {pathname === "/how-it-works" && <JourneyStory />}
        {pathname === "/about" && <AboutStory />}
        {pathname === "/faq" && (
          <div className="rx-wrap">
            <header className="rx-story-intro">
              <p className="rx-eyebrow">RushX / FAQ</p>
              <h1>Clarity before you begin.</h1>
              <p className="rx-lead">
                Practical answers about eligibility, service coverage and the
                repair journey.
              </p>
            </header>
            <section className="rx-all-faq">
              <FAQ items={faqs} />
              <div className="rx-actions">
                <RepairLink />
              </div>
            </section>
          </div>
        )}
      </main>
      <footer className="rx-footer">
        <div className="rx-wrap">
          <section
            className="rx-story-coverage"
            aria-labelledby="coverage-heading"
          >
            <h2 id="coverage-heading">Where we consider enquiries</h2>
            <p>
              Delhi NCR and Mumbai, plus eligible courier enquiries across
              India. Technical acceptance, logistics and safe transport must be
              confirmed first; wait for shipping instructions. Bengaluru
              expansion is planned, not currently offered. Nationwide onsite
              service is not guaranteed.
            </p>
          </section>
          <p className="rx-story-global-note">
            Public-page imagery is AI-generated and fictional, not photographs
            of RushX people, facilities or completed repairs.
          </p>
          <div className="rx-footer-top">
            <div>
              <Link to="/" aria-label="RushX home">
                <Logo />
              </Link>
              <p>
                Repair when possible.
                <br />
                Replace when necessary.
              </p>
              <span className="rx-small">EVChargerRepair.in</span>
            </div>
            <nav aria-label="Footer navigation">
              {nav.map(([to, label]) => (
                <Link key={to} to={to}>
                  {label}
                </Link>
              ))}
              <Link to="/repairs/new">Request a repair</Link>
              <Link to="/repairs">Track a repair</Link>
            </nav>
          </div>
          <div className="rx-footer-bottom">
            <p>
              Independent, multi-brand service. No manufacturer authorization
              claimed.
            </p>
            <span>© {new Date().getFullYear()} RushX</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
