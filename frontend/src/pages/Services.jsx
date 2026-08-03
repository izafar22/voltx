import { Reveal } from "@/components/shared/Reveal";
import { QuoteDialog } from "@/components/shared/QuoteDialog";
import { Button } from "@/components/ui/button";
import { Factory, Wrench, Cpu, ShieldCheck, Check } from "lucide-react";

const services = [
  { icon: Factory, title: "Manufacturing", desc: "Design and manufacture of AC/DC EV chargers, BESS units and solar inverters at our India facility.", points: ["In-house R&D", "OEM & private-label", "BIS-compliant builds", "Bulk production"] },
  { icon: Wrench, title: "Installation", desc: "Certified site survey, load assessment and professional installation for homes, businesses and stations.", points: ["Free site survey", "Load balancing setup", "Cabling & safety", "Commissioning & handover"] },
  { icon: Cpu, title: "Repair (PCB-level)", desc: "Multi-brand, board-level repair capability — we fix what others replace, saving you cost and downtime.", points: ["Component-level diagnosis", "Multi-brand support", "Genuine parts", "Fast turnaround"] },
  { icon: ShieldCheck, title: "AMC & Maintenance", desc: "Annual maintenance contracts with preventive visits, priority support and predictable costs.", points: ["Tiered plans", "Preventive visits", "Priority response", "Health reporting"] },
];

export default function Services() {
  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-24" data-testid="services-page">
      <Reveal>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">What we do</p>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl font-extrabold tracking-tighter">Full lifecycle services</h1>
        <p className="mt-4 text-muted-foreground max-w-2xl">From manufacturing to lifetime maintenance — RUSHX is your single accountable partner for clean energy infrastructure.</p>
      </Reveal>
      <div className="mt-12 grid gap-6 md:grid-cols-2">
        {services.map((s, i) => (
          <Reveal key={s.title} delay={(i % 2) * 0.1}>
            <div className="h-full rounded-2xl border border-border bg-card p-8 hover:-translate-y-1 transition-transform duration-300">
              <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center"><s.icon className="h-6 w-6 text-primary" /></div>
              <h3 className="mt-4 font-display font-bold text-xl">{s.title}</h3>
              <p className="mt-2 text-muted-foreground">{s.desc}</p>
              <ul className="mt-4 grid grid-cols-2 gap-2">
                {s.points.map((p) => <li key={p} className="flex items-center gap-1.5 text-sm"><Check className="h-4 w-4 text-primary" /> {p}</li>)}
              </ul>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-14 text-center">
        <QuoteDialog title="Talk to our team" trigger={<Button size="lg" className="rounded-full h-13 px-8" data-testid="services-cta-btn">Discuss your project</Button>} />
      </Reveal>
    </div>
  );
}
