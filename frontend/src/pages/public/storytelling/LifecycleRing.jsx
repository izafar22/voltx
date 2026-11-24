import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, MessageCircle, Pause, Play } from "lucide-react";
import { Link } from "react-router-dom";
import { Logo } from "../../../components/Logo";
import { lifecycleStages } from "./lifecycleData";
import "./LifecycleRing.css";

const AUTO_ADVANCE_MS = 3600;
const CIRCUMFERENCE = 263.9;
const stagePositions = [
  ["50%", "4%"], ["78%", "16%"], ["92%", "50%"], ["78%", "84%"],
  ["50%", "96%"], ["22%", "84%"], ["8%", "50%"], ["22%", "16%"],
];

const useReducedMotion = () => {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia
      ? window.matchMedia(query).matches
      : false,
  );
  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const media = window.matchMedia(query);
    const update = () => setReduced(media.matches);
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);
  return reduced;
};

export function LifecycleRing({ compact = false, headingLevel = "h2" }) {
  const [index, setIndex] = useState(0);
  const [explicitPaused, setExplicitPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);
  const [visible, setVisible] = useState(true);
  const [documentHidden, setDocumentHidden] = useState(
    () => typeof document !== "undefined" && document.hidden,
  );
  const [manualAnnouncement, setManualAnnouncement] = useState("");
  const rootRef = useRef(null);
  const reducedMotion = useReducedMotion();
  const paused =
    explicitPaused || hovered || focusWithin || !visible || documentHidden || reducedMotion;
  const stage = lifecycleStages[index];
  const Heading = headingLevel;
  const progress = useMemo(
    () => CIRCUMFERENCE - (CIRCUMFERENCE * (index + 1)) / lifecycleStages.length,
    [index],
  );

  useEffect(() => {
    const onVisibility = () => setDocumentHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    if (!rootRef.current || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.08 },
    );
    observer.observe(rootRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (paused) return undefined;
    const timer = window.setInterval(
      () => setIndex((current) => (current + 1) % lifecycleStages.length),
      AUTO_ADVANCE_MS,
    );
    return () => window.clearInterval(timer);
  }, [paused]);

  const select = (next) => {
    const selectedIndex = (next + lifecycleStages.length) % lifecycleStages.length;
    setIndex(selectedIndex);
    setManualAnnouncement(
      `Milestone ${selectedIndex + 1} of ${lifecycleStages.length}: ${lifecycleStages[selectedIndex].title}`,
    );
  };
  const focusLeaves = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) setFocusWithin(false);
  };

  return (
    <section
      className={`rx-lifecycle${compact ? " is-compact" : ""}${paused ? " is-paused" : ""}`}
      aria-labelledby={`lifecycle-title-${compact ? "home" : "full"}`}
      ref={rootRef}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocusWithin(true)}
      onBlur={focusLeaves}
    >
      <header className="rx-lifecycle-intro">
        <div>
          <p className="rx-eyebrow">Delhi / NCR EV charger repair</p>
          <Heading id={`lifecycle-title-${compact ? "home" : "full"}`}>
            A repair system you can see, trust, and follow.
          </Heading>
        </div>
        <div className="rx-lifecycle-promise">
          <p>
            Every important decision is recorded. Follow the repair lifecycle in
            your RushX account and receive optional WhatsApp milestones.
          </p>
          <div className="rx-lifecycle-legend" aria-label="Lifecycle state legend">
            <span><i className="is-current" />Current stage</span>
            <span><i />Recorded stage</span>
          </div>
        </div>
      </header>

      <div className="rx-lifecycle-heading">
        <div>
          <p className="rx-eyebrow">The RushX repair lifecycle</p>
          <h2>Watch the journey. Pause anywhere.</h2>
        </div>
        <button
          type="button"
          className="rx-lifecycle-pause"
          aria-pressed={explicitPaused}
          onClick={() => setExplicitPaused((value) => !value)}
        >
          {explicitPaused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}
          {explicitPaused ? "Play loop" : "Pause loop"}
        </button>
      </div>

      <div className="rx-lifecycle-layout">
        <div className="rx-lifecycle-orbit" aria-label="Eight-stage repair lifecycle">
          <svg className="rx-lifecycle-track" viewBox="0 0 100 100" aria-hidden="true">
            <circle cx="50" cy="50" r="42" pathLength="263.9" />
            <circle
              className="rx-lifecycle-progress"
              cx="50"
              cy="50"
              r="42"
              pathLength="263.9"
              style={{ strokeDashoffset: progress }}
            />
          </svg>
          <div className="rx-lifecycle-core" aria-hidden="true">
            <Logo />
            <span>Repair lifecycle</span>
            <b>{String(index + 1).padStart(2, "0")} / 08</b>
          </div>
          {lifecycleStages.map((item, itemIndex) => (
            <button
              type="button"
              className={`rx-lifecycle-node${itemIndex === index ? " is-selected" : ""}${itemIndex < index ? " is-complete" : ""}`}
              data-stage={item.id}
              key={item.id}
              aria-pressed={itemIndex === index}
              onClick={() => select(itemIndex)}
              style={{ "--stage-x": stagePositions[itemIndex][0], "--stage-y": stagePositions[itemIndex][1] }}
            >
              <small>{String(itemIndex + 1).padStart(2, "0")}</small>
              <span>{item.short}</span>
            </button>
          ))}
          <aside
            className="rx-lifecycle-message"
            aria-label="Illustrative WhatsApp milestone"
            key={`message-${stage.id}`}
          >
            <div>
              <span className="rx-lifecycle-message-icon"><MessageCircle aria-hidden="true" /></span>
              <p><strong>RushX</strong><small>WhatsApp milestone <i aria-hidden="true">• • •</i></small></p>
            </div>
            <p>{stage.message}</p>
            <small>Illustrative preview</small>
          </aside>
        </div>

        <p className="sr-only" aria-live="polite" aria-atomic="true">
          {manualAnnouncement}
        </p>
        <article className="rx-lifecycle-detail" key={`detail-${stage.id}`}>
          <div className="rx-lifecycle-meta">
            <span>Milestone {String(index + 1).padStart(2, "0")}</span>
            <span className="rx-lifecycle-recorded">● {stage.decision ? "Your decision" : "Recorded"}</span>
          </div>
          <h3>{stage.title}</h3>
          <p>{stage.description}</p>
          <dl>
            <div><dt>Charger location</dt><dd>{stage.location}</dd></div>
            <div><dt>Who acts next</dt><dd>{stage.nextActor}</dd></div>
          </dl>
          <div className="rx-lifecycle-control">
            <strong>{stage.decision ? "Your decision" : "Your control"}</strong>
            <p>{stage.control}</p>
            {stage.decision && (
              <div className="rx-lifecycle-demo" aria-label="Illustrative estimate decision">
                <span>Approve</span><span>Decline</span><small>Demonstration only</small>
              </div>
            )}
          </div>
          <div className="rx-lifecycle-nav">
            <button type="button" aria-label="Previous lifecycle stage" onClick={() => select(index - 1)}>
              <ArrowLeft aria-hidden="true" />
            </button>
            <button type="button" onClick={() => select(index + 1)}>
              Next stage <ArrowRight aria-hidden="true" />
            </button>
          </div>
          <p className="rx-lifecycle-hint">Hover, focus or use Pause loop to explore at your own pace.</p>
        </article>
      </div>

      <footer className="rx-lifecycle-actions">
        <div>
          <p className="rx-eyebrow">Have a charger fault?</p>
          <h2>Start with the problem. We’ll guide the next step.</h2>
        </div>
        <div>
          <Link className="rx-button" to="/repairs/new">Book a repair <ArrowRight aria-hidden="true" /></Link>
          <Link className="rx-lifecycle-track-link" to="/repairs">Track a repair</Link>
          {compact && <Link className="rx-lifecycle-track-link" to="/how-it-works">See the complete journey</Link>}
        </div>
      </footer>
    </section>
  );
}
