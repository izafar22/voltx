import { Reveal } from "@/components/shared/Reveal";
import { Counter } from "@/components/marketing/Counter";
import { Cpu, ShieldCheck, Clock, Leaf, Award, Users } from "lucide-react";

const reasons = [
  { icon: Cpu, title: "PCB-level repair expertise", desc: "Our engineers repair charger circuit boards down to the component — reducing e-waste and saving you the cost of full replacement." },
  { icon: ShieldCheck, title: "Engineered for Indian conditions", desc: "Every product is tested for voltage fluctuation, high ambient temperatures, dust and monsoon humidity." },
  { icon: Clock, title: "Fast, accountable turnaround", desc: "Same-day diagnostics and 24–48 hour service response across our coverage network." },
  { icon: Leaf, title: "Genuine parts, real warranty", desc: "Only OEM-grade components with documented warranty on every install and repair." },
  { icon: Award, title: "Enterprise-grade quality", desc: "Trusted by fleet operators, government projects and OEM partners nationwide." },
  { icon: Users, title: "End-to-end partner", desc: "Manufacturing, installation, repair and AMC — one team owns the entire lifecycle." },
];

const testimonials = [
  { q: "RUSHX repaired 40 chargers other vendors said were dead. Their PCB team is exceptional.", n: "Fleet Operations Head", c: "Logistics Company, Pune" },
  { q: "The 22kW commercial units have run flawlessly across our 12 hotels for two years.", n: "Facilities Director", c: "Hospitality Group, Mumbai" },
  { q: "Professional install, transparent AMC, and genuinely fast support. A premium partner.", n: "Society Secretary", c: "Housing Society, Bengaluru" },
];

export default function WhyUs() {
  return (
    <div data-testid="why-page">
      <section className="max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-24">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Why RUSHX</p>
          <h1 className="mt-3 font-display text-4xl sm:text-5xl font-extrabold tracking-tighter">The trusted, premium choice</h1>
          <p className="mt-4 text-muted-foreground max-w-2xl">We combine manufacturing depth, board-level repair skill and genuine service accountability — the reason India's most demanding customers choose us.</p>
        </Reveal>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {reasons.map((r, i) => (
            <Reveal key={r.title} delay={(i % 3) * 0.08}>
              <div className="h-full rounded-2xl border border-border bg-card p-6 hover:-translate-y-1 transition-transform duration-300">
                <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center"><r.icon className="h-6 w-6 text-primary" /></div>
                <h3 className="mt-4 font-display font-bold text-lg">{r.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{r.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="bg-slate-950 text-white">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 py-16 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[{ to: 8, s: "+", l: "Years of expertise" }, { to: 500, s: "+", l: "Enterprise clients" }, { to: 25000, s: "+", l: "Repairs completed" }, { to: 15, s: "", l: "OEM partners" }].map((x, i) => (
            <Reveal key={x.l} delay={i * 0.1} className="text-center">
              <div className="font-display text-3xl sm:text-4xl font-extrabold text-emerald-400"><Counter to={x.to} suffix={x.s} /></div>
              <div className="mt-1 text-sm text-slate-400">{x.l}</div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-24">
        <Reveal><h2 className="font-display text-3xl font-bold text-center">What our customers say</h2></Reveal>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {testimonials.map((t, i) => (
            <Reveal key={t.n} delay={i * 0.1}>
              <div className="h-full rounded-2xl border border-border bg-card p-6">
                <p className="text-lg leading-relaxed">"{t.q}"</p>
                <div className="mt-5 pt-4 border-t border-border">
                  <p className="font-semibold">{t.n}</p>
                  <p className="text-sm text-muted-foreground">{t.c}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>
    </div>
  );
}
