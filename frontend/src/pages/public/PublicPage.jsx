import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Menu,
  X,
  Zap,
  Check,
  MapPin,
} from "lucide-react";
import { Logo } from "../../components/Logo";
import { useAuth } from "../../context/AuthContext";
import { homeFor } from "../../components/ProtectedRoute";
import { services, steps, faqs } from "./content";
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
const RepairLink = ({ children = "Request a repair", secondary = false }) => (
  <Link
    className={`rx-button ${secondary ? "rx-secondary" : ""}`}
    to="/repairs/new"
  >
    {children}
    <ArrowUpRight size={18} aria-hidden="true" />
  </Link>
);
function Journey() {
  return (
    <ol className="rx-journey">
      {steps.map(([title, text], i) => (
        <li key={title}>
          <span className="rx-step">0{i + 1}</span>
          <h3>{title}</h3>
          <p>{text}</p>
        </li>
      ))}
    </ol>
  );
}
function Questions({ compact = false }) {
  return (
    <div className="rx-questions">
      {faqs.slice(0, compact ? 4 : undefined).map(([q, a]) => (
        <details key={q}>
          <summary>
            {q}
            <span aria-hidden="true">+</span>
          </summary>
          <p>{a}</p>
        </details>
      ))}
    </div>
  );
}
function Coverage() {
  return (
    <section className="rx-coverage rx-section">
      <div>
        <p className="rx-eyebrow">Service coverage</p>
        <h2>
          Local assessment.
          <br />A wider reach, by courier.
        </h2>
      </div>
      <div>
        <div className="rx-locations">
          <span>
            <MapPin size={18} aria-hidden="true" />
            Delhi NCR
          </span>
          <span>
            <MapPin size={18} aria-hidden="true" />
            Mumbai
          </span>
        </div>
        <p>
          Eligible courier-based repair enquiries are considered from across
          India. Acceptance, logistics and safe transport must be confirmed
          first. Please do not ship equipment before receiving instructions.
        </p>
        <p className="rx-small">
          Bengaluru expansion is planned, not currently offered. Nationwide
          onsite service is not guaranteed.
        </p>
      </div>
    </section>
  );
}
function FinalCTA() {
  return (
    <section className="rx-final">
      <div>
        <p className="rx-eyebrow">Start with an assessment</p>
        <h2>
          A fault doesn’t have to
          <br />
          mean the end.
        </h2>
        <p>Tell us about your charger. Let’s explore what’s feasible.</p>
      </div>
      <RepairLink />
    </section>
  );
}
function Illustration() {
  return (
    <div
      className="rx-illustration"
      role="img"
      aria-label="Illustration of a charger connected to a diagnostic control board"
    >
      <div className="rx-diagram-label">
        A closer look. A considered next step.
      </div>
      <div className="rx-charger">
        <Zap size={42} aria-hidden="true" />
        <div className="rx-charger-screen">
          <span />
          DIAGNOSTICS
        </div>
        <div className="rx-charger-lines" />
        <div className="rx-cable" />
      </div>
      <div className="rx-board">
        <div className="rx-chip">
          <Zap size={30} aria-hidden="true" />
        </div>
        {[1, 2, 3, 4].map((n) => (
          <i key={n} />
        ))}
        <span>CONTROL BOARD</span>
      </div>
      <div className="rx-diagram-note">
        <Check size={17} aria-hidden="true" />
        Understand the fault first
      </div>
      <span className="rx-illustrative">
        ILLUSTRATIVE DIAGRAM · NOT A FACILITY PHOTO
      </span>
    </div>
  );
}
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
          <button
            className="rx-menu-toggle"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="public-navigation"
            onClick={() => setOpen(!open)}
          >
            {open ? <X /> : <Menu />}
          </button>
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
            <Link
              className="rx-account"
              to={user ? homeFor(user.role) : "/login"}
            >
              {user ? "My account" : "Sign in"}
              <ArrowUpRight size={15} aria-hidden="true" />
            </Link>
          </nav>
        </div>
      </header>
      <main id="public-main" tabIndex={-1} ref={main}>
        {pathname === "/" ? (
          <>
            <section className="rx-hero rx-wrap">
              <div>
                <p className="rx-eyebrow">
                  <span />
                  Independent EV charger repair enquiries
                </p>
                <h1>
                  Repair when possible.
                  <br />
                  <em>Replace when necessary.</em>
                </h1>
                <p className="rx-lead">
                  A considered next step for your faulty EV charger. RushX
                  assesses multi-brand chargers and electronics to understand
                  what can be repaired.
                </p>
                <div className="rx-actions">
                  <RepairLink />
                  <Link className="rx-text-link" to="/services">
                    Explore our services{" "}
                    <ArrowRight size={18} aria-hidden="true" />
                  </Link>
                </div>
                <p className="rx-hero-coverage">
                  Delhi NCR · Mumbai · Eligible courier enquiries across India
                </p>
              </div>
              <Illustration />
            </section>
            <div className="rx-principles">
              <div className="rx-wrap">
                <span>
                  <Check size={17} />
                  Multi-brand assessment
                </span>
                <span>
                  <Check size={17} />
                  Your approval before repair
                </span>
                <span>
                  <Check size={17} />
                  Feasibility comes first
                </span>
              </div>
            </div>
            <section className="rx-section rx-wrap">
              <div className="rx-section-heading">
                <div>
                  <p className="rx-eyebrow">What we assess</p>
                  <h2>
                    Different chargers.
                    <br />
                    The same careful approach.
                  </h2>
                </div>
                <p>
                  From control boards to power modules, we start with the fault
                  — and assess the options before recommending a repair.
                </p>
              </div>
              <div className="rx-service-grid">
                {services.map(({ id, icon: Icon, name, short }, i) => (
                  <Link
                    className="rx-service-card"
                    to={`/services#${id}`}
                    key={id}
                  >
                    <div className="rx-card-top">
                      <Icon size={30} aria-hidden="true" />
                      <span>0{i + 1}</span>
                    </div>
                    <h3>{name}</h3>
                    <p>{short}</p>
                    <span className="rx-card-link">
                      Explore service{" "}
                      <ArrowUpRight size={18} aria-hidden="true" />
                    </span>
                  </Link>
                ))}
              </div>
            </section>
            <section className="rx-mission">
              <div className="rx-wrap rx-split">
                <p className="rx-eyebrow">Our repair-first philosophy</p>
                <div>
                  <h2>
                    Understand the problem.
                    <br />
                    Consider the possibilities.
                  </h2>
                  <p>
                    Replacement can be the right answer. But it should be a
                    considered one. We explore repair where technically
                    feasible, helping you make an informed decision about your
                    equipment.
                  </p>
                  <Link className="rx-text-link" to="/about">
                    Why RushX <ArrowRight size={18} />
                  </Link>
                </div>
              </div>
            </section>
            <section className="rx-wrap rx-section">
              <div className="rx-section-heading">
                <div>
                  <p className="rx-eyebrow">From enquiry to return</p>
                  <h2>A clear path forward.</h2>
                </div>
                <Link className="rx-text-link" to="/how-it-works">
                  See the full process <ArrowRight size={18} />
                </Link>
              </div>
              <Journey />
            </section>
            <div className="rx-wrap">
              <Coverage />
              <section className="rx-section rx-faq-preview">
                <div>
                  <p className="rx-eyebrow">Before you begin</p>
                  <h2>A few useful answers.</h2>
                  <Link className="rx-text-link" to="/faq">
                    All questions <ArrowRight size={18} />
                  </Link>
                </div>
                <Questions compact />
              </section>
              <FinalCTA />
            </div>
          </>
        ) : (
          <div className="rx-wrap">
            <section className="rx-page-intro">
              <p className="rx-eyebrow">
                RushX / {nav.find(([to]) => to === pathname)?.[1]}
              </p>
              <h1>
                {pathname === "/services"
                  ? "Repair starts with understanding."
                  : pathname === "/how-it-works"
                    ? "Know what happens next."
                    : pathname === "/about"
                      ? "A repair-first way of thinking."
                      : "Clarity before you begin."}
              </h1>
              <p className="rx-lead">
                {pathname === "/services"
                  ? "Independent, multi-brand assessment for EV charging equipment and electronics. Every enquiry is subject to technical acceptance."
                  : pathname === "/how-it-works"
                    ? "Five considered steps, with technical acceptance and your approval built into the process."
                    : pathname === "/about"
                      ? "Repair when possible. Replace when necessary. That’s the principle behind RushX."
                      : "Practical answers about eligibility, service coverage and the repair journey."}
              </p>
            </section>
            {pathname === "/services" && (
              <>
                <div
                  className="rx-service-jumps"
                  aria-label="Service categories"
                >
                  {services.map((s) => (
                    <a key={s.id} href={`#${s.id}`}>
                      {s.name}
                      <ArrowUpRight size={15} />
                    </a>
                  ))}
                </div>
                {services.map(
                  (
                    {
                      id,
                      icon: Icon,
                      name,
                      description,
                      symptoms,
                      eligibility,
                    },
                    i,
                  ) => (
                    <section id={id} className="rx-service-detail" key={id}>
                      <div>
                        <span className="rx-eyebrow">
                          0{i + 1} / Service enquiry
                        </span>
                        <Icon size={38} aria-hidden="true" />
                        <h2>{name}</h2>
                        <p>{description}</p>
                        <RepairLink secondary>Request an assessment</RepairLink>
                      </div>
                      <div className="rx-detail-notes">
                        <h3>Symptoms worth sharing</h3>
                        <p>
                          {symptoms} These are examples, not a remote diagnosis.
                        </p>
                        <h3>What determines eligibility</h3>
                        <p>{eligibility}</p>
                        <p className="rx-small">
                          Do not open, modify or energize faulty equipment.
                          Share only information and photos you can obtain
                          safely.
                        </p>
                      </div>
                    </section>
                  ),
                )}
                <Coverage />
              </>
            )}
            {pathname === "/how-it-works" && (
              <>
                <Journey />
                <section className="rx-preparation rx-section">
                  <div>
                    <p className="rx-eyebrow">Prepare your enquiry</p>
                    <h2>
                      A little detail helps
                      <br />
                      the assessment.
                    </h2>
                    <p>
                      Share what you know. You do not need to diagnose the fault
                      yourself.
                    </p>
                  </div>
                  <ul>
                    {[
                      "Charger brand, exact model and type",
                      "Power rating and fault symptoms or codes",
                      "Your location and clear photos",
                      "Wait for acceptance before shipping",
                    ].map((item) => (
                      <li key={item}>
                        <Check size={19} />
                        {item}
                      </li>
                    ))}
                  </ul>
                </section>
                <p className="rx-notice">
                  Safety first: do not open or energize faulty equipment to
                  collect information. Repair feasibility, charges, logistics
                  and any warranty terms are confirmed through assessment and
                  quotation.
                </p>
                <Coverage />
              </>
            )}
            {pathname === "/about" && (
              <>
                <section className="rx-about-grid">
                  <div className="rx-about-statement">
                    <Zap size={44} aria-hidden="true" />
                    <h2>
                      Good decisions
                      <br />
                      start with
                      <br />
                      <em>understanding.</em>
                    </h2>
                  </div>
                  <div>
                    <p className="rx-eyebrow">The RushX approach</p>
                    <h2>
                      Independent by design.
                      <br />
                      Practical by principle.
                    </h2>
                    <p>
                      RushX, at EVChargerRepair.in, is an independent,
                      multi-brand EV charger repair enquiry and electronics
                      service for individual customers.
                    </p>
                    <p>
                      Our mission is to assess repair feasibility before
                      unnecessary replacement. We explore component-level repair
                      where suitable, and recognize when replacement is
                      necessary.
                    </p>
                    <p>
                      We do not guarantee every charger can be repaired, and we
                      do not claim manufacturer authorization. The equipment,
                      available parts and safe testing options guide each
                      decision.
                    </p>
                  </div>
                </section>
                <section className="rx-values rx-section">
                  {[
                    [
                      "Technical honesty",
                      "Feasibility comes before a promise. We assess compatibility and the fault before accepting work.",
                    ],
                    [
                      "Informed approval",
                      "Inspection and a quotation give you a clear decision point before an authorized repair.",
                    ],
                    [
                      "Responsible scope",
                      "Repair and testing follow the accepted scope. Service documentation and quotation terms set expectations.",
                    ],
                  ].map(([title, text]) => (
                    <div key={title}>
                      <h3>{title}</h3>
                      <p>{text}</p>
                    </div>
                  ))}
                </section>
                <Coverage />
              </>
            )}
            {pathname === "/faq" && (
              <section className="rx-all-faq">
                <Questions />
                <p className="rx-notice">
                  Have an equipment-specific question?{" "}
                  <Link to="/repairs/new">Submit a repair enquiry</Link> with
                  your model and fault details so the technical team can assess
                  it.
                </p>
              </section>
            )}
            <FinalCTA />
          </div>
        )}
      </main>
      <footer className="rx-footer">
        <div className="rx-wrap">
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
