import { Link } from "react-router-dom";
import { ArrowRight, ArrowUpRight, Check } from "lucide-react";
import { services, steps } from "../content";
import { StoryImage } from "./StoryImage";
import "./StoryPages.css";

export function RepairLink({
  children = "Request a repair",
  secondary = false,
}) {
  return (
    <Link
      className={`rx-button ${secondary ? "rx-secondary" : ""}`}
      to="/repairs/new"
    >
      {children}
      <ArrowUpRight size={18} aria-hidden="true" />
    </Link>
  );
}
const TextLink = ({ to, children }) => (
  <Link className="rx-text-link" to={to}>
    {children}
    <ArrowRight size={18} aria-hidden="true" />
  </Link>
);
const Intro = ({ label, title, children }) => (
  <header className="rx-story-intro">
    <p className="rx-eyebrow">{label}</p>
    <h1>{title}</h1>
    <p className="rx-lead">{children}</p>
  </header>
);

export function HomeStory() {
  return (
    <div className="rx-wrap rx-story-home">
      <section className="rx-story-hero">
        <div>
          <p className="rx-eyebrow">Independent EV charger repair enquiries</p>
          <h1>
            Repair when possible.
            <br />
            <em>Replace when necessary.</em>
          </h1>
          <p className="rx-lead">
            A charging fault doesn’t always mean replacing the charger. RushX
            assesses multi-brand EV chargers and electronics to find a
            technically sound next step.
          </p>
          <div className="rx-actions">
            <RepairLink />
            <TextLink to="/services">Explore our services</TextLink>
          </div>
        </div>
        <StoryImage
          asset="hero"
          priority
          caption="Fictional diagnostic scene. Equipment and readings are illustrative."
        />
      </section>
      <section
        className="rx-story-services"
        aria-labelledby="home-services-title"
      >
        <div className="rx-story-heading">
          <div>
            <p className="rx-eyebrow">What can we assess?</p>
            <h2 id="home-services-title">From the charger to the circuit.</h2>
          </div>
          <p>
            Share the model and symptoms first. We confirm compatibility before
            accepting equipment.
          </p>
        </div>
        <div className="rx-story-preview-grid">
          {services.map(({ id, icon: Icon, name, short }, i) => (
            <Link to={`/services#${id}`} key={id} className="rx-story-preview">
              <span className="rx-story-preview-top">
                <Icon aria-hidden="true" size={28} />
                <span>0{i + 1}</span>
              </span>
              <h3>{name}</h3>
              <p>{short}</p>
              <span className="rx-text-link">
                Explore service <ArrowUpRight size={16} aria-hidden="true" />
              </span>
            </Link>
          ))}
        </div>
      </section>
      <section className="rx-story-next">
        <StoryImage
          asset="testing"
          caption="Fictional workbench. No test result or certification is depicted."
        />
        <div>
          <p className="rx-eyebrow">A clear decision, before repair</p>
          <h2>
            Understand the fault.
            <br />
            Approve the next step.
          </h2>
          <p>
            Technical acceptance comes first. After inspection, review the
            proposed scope and quotation before authorizing work. Repair and
            testing follow the agreed scope.
          </p>
          <div className="rx-story-link-row">
            <TextLink to="/how-it-works">See the five steps</TextLink>
            <TextLink to="/about">Why RushX</TextLink>
          </div>
        </div>
      </section>
    </div>
  );
}

export function ServicesStory() {
  return (
    <div className="rx-wrap rx-story-services-page">
      <Intro
        label="RushX / Services"
        title="Different equipment. A focused assessment."
      >
        Independent assessment for EV chargers, control boards and supporting
        electronics. Start with your equipment details, not a replacement order.
      </Intro>
      <nav className="rx-service-jumps" aria-label="Service categories">
        {services.map((s) => (
          <a key={s.id} href={`#${s.id}`}>
            {s.name}
            <ArrowUpRight size={15} aria-hidden="true" />
          </a>
        ))}
      </nav>
      <p className="rx-story-disclosure">
        AI-generated equipment concepts, not RushX inventory or a list of
        supported models.
      </p>
      {services.map(({ id, name, description, symptoms, eligibility }, i) => (
        <section className="rx-story-service" id={id} key={id}>
          <StoryImage asset={id} />
          <div>
            <p className="rx-eyebrow">0{i + 1} / Equipment assessment</p>
            <h2>{name}</h2>
            <p>{description}</p>
            <dl>
              <dt>What you might notice</dt>
              <dd>{symptoms}</dd>
              <dt>What the assessment considers</dt>
              <dd>{eligibility}</dd>
            </dl>
            <RepairLink secondary>Request an assessment</RepairLink>
          </div>
        </section>
      ))}
      <aside className="rx-story-safety">
        <Check aria-hidden="true" size={22} />
        <p>
          Share only details and photos you can obtain safely. Do not open,
          modify or energize faulty equipment. Symptoms are a starting point,
          not a remote diagnosis.
        </p>
      </aside>
    </div>
  );
}

export function JourneyStory() {
  return (
    <div className="rx-wrap">
      <Intro
        label="RushX / How it works"
        title="Your repair journey, without the guesswork."
      >
        Five steps from first enquiry to return, with technical acceptance and
        your approval built in.
      </Intro>
      <p className="rx-story-disclosure">
        AI-generated fictional scenes explain the journey; they are not
        photographs of RushX staff, facilities or actual customer repairs.
      </p>
      <ol className="rx-story-journey">
        {steps.map(([title, text], i) => (
          <li key={title}>
            <StoryImage asset={`step${i + 1}`} />
            <div>
              <span className="rx-story-number">0{i + 1}</span>
              <h2>{title}</h2>
              <p>{text}</p>
              {i === 0 && (
                <>
                  <p className="rx-small">
                    Do not open or energize equipment to gather information.
                  </p>
                  <RepairLink />
                </>
              )}
              {i === 2 && (
                <p className="rx-small">
                  Charges and any warranty terms are specific to your quotation.
                </p>
              )}
              {i === 4 && (
                <p className="rx-small">
                  Wait for technical acceptance and shipping instructions before
                  sending anything.
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
      <aside className="rx-story-safety">
        <p>
          Repair is not guaranteed. Model compatibility, fault condition, parts
          and safe testing options determine what is feasible.{" "}
          <Link to="/faq">Read the repair FAQ</Link>.
        </p>
      </aside>
    </div>
  );
}

export function AboutStory() {
  return (
    <div className="rx-wrap">
      <Intro label="RushX / About" title="A repair-first way of thinking.">
        Repair when possible. Replace when necessary. That’s the principle
        behind RushX.
      </Intro>
      <section className="rx-story-about">
        <StoryImage
          asset="about"
          priority
          caption="AI-generated exploded equipment concept, not an assembly guide or a supported-model claim."
        />
        <div>
          <p className="rx-eyebrow">Look beyond the enclosure</p>
          <h2>
            The whole charger.
            <br />
            The individual fault.
          </h2>
          <p>
            RushX, at EVChargerRepair.in, is an independent, multi-brand EV
            charger repair enquiry and electronics service for individual
            customers.
          </p>
          <p>
            Our mission is to explore repair feasibility before unnecessary
            replacement. A component-level fault may have a repair path; damaged
            equipment, unavailable parts or unsafe testing conditions may make
            replacement the responsible choice.
          </p>
          <TextLink to="/services">Explore what we assess</TextLink>
        </div>
      </section>
      <section className="rx-story-values" aria-label="Our principles">
        {[
          [
            "01",
            "Technical honesty",
            "Feasibility comes before a promise. We do not guarantee every charger can be repaired or claim manufacturer authorization.",
          ],
          [
            "02",
            "Your informed decision",
            "Inspection and a quotation give you a clear decision point. Work proceeds only within the scope you authorize.",
          ],
          [
            "03",
            "Responsible repair",
            "Testing, return arrangements and service documentation follow the accepted scope. Any warranty must be specified in the quotation.",
          ],
        ].map(([number, title, text]) => (
          <article key={title}>
            <span className="rx-story-number">{number}</span>
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </section>
      <div className="rx-story-about-action">
        <p>Have a charger fault you’d like assessed?</p>
        <RepairLink />
      </div>
    </div>
  );
}
