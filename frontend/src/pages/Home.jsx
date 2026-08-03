import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Zap, Wrench, ShieldCheck, Cpu, Clock, Leaf, BatteryCharging, Sun, Building2, Car, Home as HomeIcon, Landmark } from "lucide-react";
import { api } from "@/lib/api";
import { Reveal } from "@/components/shared/Reveal";
import { Counter } from "@/components/marketing/Counter";
import { QuoteDialog } from "@/components/shared/QuoteDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const heroImg = "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600";

const whyItems = [
  { icon: Cpu, title: "PCB-level repair", desc: "In-house board repair for all major charger brands — not just replacements." },
  { icon: ShieldCheck, title: "Built for India", desc: "Engineered for voltage fluctuations, dust, heat and monsoon conditions." },
  { icon: Clock, title: "Fast turnaround", desc: "Same-day diagnostics and 24–48 hr response for most service requests." },
  { icon: Leaf, title: "Genuine parts", desc: "Only OEM-grade components with warranty on every repair and install." },
];

const segments = [
  { icon: HomeIcon, title: "Residential", to: "/segments" },
  { icon: Building2, title: "Commercial", to: "/segments" },
  { icon: Car, title: "Fleet", to: "/segments" },
  { icon: Landmark, title: "Government", to: "/segments" },
];

export default function Home() {
  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: async () => (await api.get("/products")).data });

  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img src={heroImg} alt="EV charging" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-slate-950/70 to-slate-950/30" />
        </div>
        <div className="relative max-w-7xl mx-auto px-5 lg:px-8 py-28 lg:py-40">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }} className="max-w-2xl">
            <Badge className="bg-primary/20 text-emerald-300 border-primary/30 mb-5 rounded-full px-4 py-1.5" data-testid="hero-badge">
              <Zap className="h-3.5 w-3.5 mr-1.5" fill="currentColor" /> India's Trusted EV Charging Solutions
            </Badge>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tighter text-white leading-[1.05]">
              Powering India's <span className="text-primary">electric</span> future
            </h1>
            <p className="mt-6 text-lg text-slate-300 max-w-xl leading-relaxed">
              We manufacture, install, repair and maintain EV chargers, PowerBoy battery storage and Hearth solar inverters — enterprise-grade energy solutions built for Indian conditions.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <QuoteDialog title="Request a Quote" trigger={
                <Button size="lg" className="rounded-full h-13 px-7 text-base" data-testid="hero-quote-btn">
                  Request a quote <ArrowRight className="h-5 w-5 ml-2" />
                </Button>} />
              <Link to="/products">
                <Button size="lg" variant="outline" className="rounded-full h-13 px-7 text-base bg-white/10 border-white/30 text-white hover:bg-white/20" data-testid="hero-products-btn">
                  Explore products
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* STATS */}
      <section className="border-b border-border bg-secondary/30">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 py-14 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { to: 12500, suffix: "+", label: "Chargers installed" },
            { to: 48, suffix: "", label: "Cities served" },
            { to: 3200000, suffix: "", label: "kWh delivered" },
            { to: 99, suffix: "%", label: "Uptime guaranteed" },
          ].map((s, i) => (
            <Reveal key={s.label} delay={i * 0.1} className="text-center">
              <div className="font-display text-3xl sm:text-4xl font-extrabold text-primary"><Counter to={s.to} suffix={s.suffix} /></div>
              <div className="mt-1 text-sm text-muted-foreground">{s.label}</div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* PRODUCTS */}
      <section className="max-w-7xl mx-auto px-5 lg:px-8 py-20 lg:py-28">
        <Reveal className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Our products</p>
          <h2 className="mt-3 font-display text-3xl sm:text-4xl font-bold tracking-tight">A complete clean-energy stack</h2>
          <p className="mt-4 text-muted-foreground">From portable home chargers to commercial fast chargers, battery storage and solar — one trusted partner.</p>
        </Reveal>
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {products.slice(0, 6).map((p, i) => (
            <Reveal key={p.slug} delay={(i % 3) * 0.1}>
              <Link to={`/products/${p.slug}`} data-testid={`home-product-${p.slug}`}
                className="group block rounded-2xl overflow-hidden border border-border bg-card hover:-translate-y-1 transition-transform duration-300 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none">
                <div className="aspect-[16/10] overflow-hidden">
                  <img src={p.image} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                </div>
                <div className="p-5">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="rounded-full">{p.category}</Badge>
                    <span className="text-xs text-muted-foreground">{p.power}</span>
                  </div>
                  <h3 className="mt-3 font-display font-bold text-lg group-hover:text-primary transition-colors duration-200">{p.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{p.tagline}</p>
                  <p className="mt-3 text-sm font-semibold text-primary flex items-center">View details <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform duration-200" /></p>
                </div>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* SERVICES STRIP */}
      <section className="bg-slate-950 text-white">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 py-20 grid gap-10 lg:grid-cols-2 items-center">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">End-to-end services</p>
            <h2 className="mt-3 font-display text-3xl sm:text-4xl font-bold">Manufacture. Install. Repair. Maintain.</h2>
            <p className="mt-4 text-slate-300">Full lifecycle support with PCB-level repair capability across multiple charger brands and genuine spare parts.</p>
            <div className="mt-8 grid sm:grid-cols-2 gap-4">
              {[{ icon: Zap, t: "Manufacturing" }, { icon: Wrench, t: "Installation" }, { icon: Cpu, t: "PCB-level Repair" }, { icon: ShieldCheck, t: "AMC Contracts" }].map((s) => (
                <div key={s.t} className="flex items-center gap-3 rounded-xl bg-white/5 border border-white/10 p-4">
                  <s.icon className="h-6 w-6 text-primary" />
                  <span className="font-medium">{s.t}</span>
                </div>
              ))}
            </div>
            <Link to="/services"><Button className="mt-8 rounded-full" data-testid="home-services-btn">All services <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
          </Reveal>
          <Reveal delay={0.15} className="grid grid-cols-2 gap-4">
            {[{ icon: BatteryCharging, t: "PowerBoy Powerwall", d: "BESS storage" }, { icon: Sun, t: "Hearth Inverter", d: "Solar hybrid" }, { icon: Car, t: "Fleet charging", d: "Depot solutions" }, { icon: Building2, t: "OEM services", d: "Private-label" }].map((c) => (
              <div key={c.t} className="rounded-2xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10 p-6">
                <c.icon className="h-8 w-8 text-emerald-400" />
                <h3 className="mt-4 font-display font-bold">{c.t}</h3>
                <p className="text-sm text-slate-400">{c.d}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      {/* WHY */}
      <section className="max-w-7xl mx-auto px-5 lg:px-8 py-20 lg:py-28">
        <Reveal className="text-center max-w-2xl mx-auto">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Why RUSHX</p>
          <h2 className="mt-3 font-display text-3xl sm:text-4xl font-bold tracking-tight">The premium choice for reliable energy</h2>
        </Reveal>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {whyItems.map((w, i) => (
            <Reveal key={w.title} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-border bg-card p-6 hover:-translate-y-1 transition-transform duration-300">
                <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center"><w.icon className="h-6 w-6 text-primary" /></div>
                <h3 className="mt-4 font-display font-bold text-lg">{w.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{w.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* SEGMENTS */}
      <section className="bg-secondary/30 border-y border-border">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 py-16 grid grid-cols-2 md:grid-cols-4 gap-5">
          {segments.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.08}>
              <Link to={s.to} className="group flex flex-col items-center text-center gap-3 rounded-2xl bg-card border border-border p-8 hover:-translate-y-1 transition-transform duration-300" data-testid={`home-segment-${s.title}`}>
                <s.icon className="h-9 w-9 text-primary group-hover:scale-110 transition-transform duration-300" />
                <span className="font-display font-semibold">{s.title}</span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-5 lg:px-8 py-20">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl bg-primary p-10 lg:p-16 text-center">
            <div className="absolute inset-0 grain opacity-30" />
            <div className="relative">
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-white">Ready to electrify your space?</h2>
              <p className="mt-3 text-emerald-50 max-w-xl mx-auto">Get a tailored quote for your home, business or fleet in under 24 hours.</p>
              <QuoteDialog title="Request a Quote" trigger={
                <Button size="lg" variant="secondary" className="mt-8 rounded-full h-13 px-8 text-base" data-testid="cta-quote-btn">
                  Get your quote <ArrowRight className="h-5 w-5 ml-2" />
                </Button>} />
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
