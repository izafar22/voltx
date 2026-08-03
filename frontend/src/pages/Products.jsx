import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Reveal } from "@/components/shared/Reveal";
import { Badge } from "@/components/ui/badge";
import { ArrowRight } from "lucide-react";

export default function Products() {
  const { data: products = [], isLoading } = useQuery({ queryKey: ["products"], queryFn: async () => (await api.get("/products")).data });
  const cats = ["EV Charger", "BESS", "Solar"];

  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-24" data-testid="products-page">
      <Reveal>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Product catalog</p>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl font-extrabold tracking-tighter">Our products</h1>
        <p className="mt-4 text-muted-foreground max-w-2xl">Enterprise-grade EV chargers, battery storage and solar inverters — engineered and supported in India.</p>
      </Reveal>

      {isLoading && <p className="mt-12 text-muted-foreground">Loading...</p>}

      {cats.map((cat) => {
        const items = products.filter((p) => p.category === cat);
        if (!items.length) return null;
        return (
          <div key={cat} className="mt-14">
            <h2 className="font-display text-2xl font-bold mb-6">{cat === "EV Charger" ? "EV Chargers" : cat === "BESS" ? "Battery Storage (BESS)" : "Solar Solutions"}</h2>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {items.map((p, i) => (
                <Reveal key={p.slug} delay={(i % 3) * 0.08}>
                  <Link to={`/products/${p.slug}`} data-testid={`product-card-${p.slug}`}
                    className="group block rounded-2xl overflow-hidden border border-border bg-card hover:-translate-y-1 transition-transform duration-300 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none">
                    <div className="aspect-[16/10] overflow-hidden">
                      <img src={p.image} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    </div>
                    <div className="p-5">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="rounded-full">{p.power}</Badge>
                        <span className="text-sm font-semibold text-primary">{p.price_range}</span>
                      </div>
                      <h3 className="mt-3 font-display font-bold text-lg group-hover:text-primary transition-colors duration-200">{p.name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{p.description}</p>
                      <p className="mt-3 text-sm font-semibold text-primary flex items-center">Details <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform duration-200" /></p>
                    </div>
                  </Link>
                </Reveal>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
