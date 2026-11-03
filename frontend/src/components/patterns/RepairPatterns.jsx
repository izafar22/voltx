import "./RepairPatterns.css";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
// Pure presentation: callers supply approved content. No auth, effects or APIs.
export function RepairJourney({ steps }) {
  return (
    <ol className="rx-journey">
      {steps.map(([title, text], index) => (
        <li key={title}>
          <span className="rx-step">{String(index + 1).padStart(2, "0")}</span>
          <h3>{title}</h3>
          <p>{text}</p>
        </li>
      ))}
    </ol>
  );
}
export function FAQ({ items }) {
  return (
    <div className="rx-questions">
      {items.map(([question, answer]) => (
        <details key={question}>
          <summary>
            {question}
            <span aria-hidden="true">+</span>
          </summary>
          <p>{answer}</p>
        </details>
      ))}
    </div>
  );
}
export function ServiceCard({ service, index = 0 }) {
  const { id, icon: Icon, name, short } = service;
  return (
    <Link className="rx-service-card" to={`/services#${id}`}>
      <div className="rx-card-top">
        <Icon size={30} aria-hidden="true" />
        <span>{String(index + 1).padStart(2, "0")}</span>
      </div>
      <h3>{name}</h3>
      <p>{short}</p>
      <span className="rx-card-link">
        Explore service <ArrowUpRight size={18} aria-hidden="true" />
      </span>
    </Link>
  );
}
