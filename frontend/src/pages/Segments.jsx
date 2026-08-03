import { Reveal } from "@/components/shared/Reveal";
import { QuoteDialog } from "@/components/shared/QuoteDialog";
import { Button } from "@/components/ui/button";
import { Home, Building2, Car, Landmark, Check } from "lucide-react";

const segments = [
  { icon: Home, title: "Residential", img: "https://images.pexels.com/photos/27355831/pexels-photo-27355831.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", desc: "Home chargers, apartment charging and rooftop solar for EV owners and families.", points: ["Portable & wallbox chargers", "Society-wide charging", "Rooftop solar + storage", "Scheduled home charging"] },
  { icon: Building2, title: "Commercial", img: "https://images.unsplash.com/photo-1717386255773-1e3037c81788?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200", desc: "Hotels, offices, dealerships and workshops needing reliable multi-user charging.", points: ["11kW & 22kW chargers", "Multi-user billing", "Backup power (BESS)", "Branded charging zones"] },
  { icon: Car, title: "Fleet", img: "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200", desc: "Depot and fleet charging with load management and predictable maintenance.", points: ["Depot fast charging", "Dynamic load balancing", "Fleet AMC contracts", "Uptime SLAs"] },
  { icon: Landmark, title: "Government", img: "https://images.unsplash.com/photo-1780445392694-c95056ed12e2?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200", desc: "Public charging infrastructure, institutions and large-scale government projects.", points: ["Tender-ready builds", "Public charging stations", "BIS-compliant equipment", "Turnkey deployment"] },
];

export default function Segments() {
  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-24" data-testid="segments-page">
      <Reveal>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Who we serve</p>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl font-extrabold tracking-tighter">Solutions for every customer</h1>
        <p className="mt-4 text-muted-foreground max-w-2xl">Tailored energy solutions across residential, commercial, fleet and government segments.</p>
      </Reveal>
      <div className="mt-12 space-y-8">
        {segments.map((s, i) => (
          <Reveal key={s.title} delay={0.05}>
            <div className={`grid gap-8 lg:grid-cols-2 items-center rounded-3xl border border-border bg-card overflow-hidden ${i % 2 ? "lg:[&>*:first-child]:order-2" : ""}`}>
              <div className="aspect-[16/11] lg:aspect-auto lg:h-full overflow-hidden">
                <img src={s.img} alt={s.title} className="w-full h-full object-cover" />
              </div>
              <div className="p-8 lg:p-10">
                <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center"><s.icon className="h-6 w-6 text-primary" /></div>
                <h2 className="mt-4 font-display text-2xl font-bold">{s.title}</h2>
                <p className="mt-2 text-muted-foreground">{s.desc}</p>
                <ul className="mt-4 grid sm:grid-cols-2 gap-2">
                  {s.points.map((p) => <li key={p} className="flex items-center gap-1.5 text-sm"><Check className="h-4 w-4 text-primary" /> {p}</li>)}
                </ul>
                <QuoteDialog title={`${s.title} enquiry`} trigger={<Button className="mt-6 rounded-full" data-testid={`segment-quote-${s.title}`}>Get a {s.title.toLowerCase()} quote</Button>} />
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
