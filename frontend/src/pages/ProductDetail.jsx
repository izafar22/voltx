import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Reveal } from "@/components/shared/Reveal";
import { QuoteDialog } from "@/components/shared/QuoteDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, ArrowLeft, MessageCircle } from "lucide-react";

export default function ProductDetail() {
  const { slug } = useParams();
  const { data: p, isLoading, isError } = useQuery({ queryKey: ["product", slug], queryFn: async () => (await api.get(`/products/${slug}`)).data });

  if (isLoading) return <div className="max-w-7xl mx-auto px-5 py-24 text-muted-foreground">Loading...</div>;
  if (isError || !p) return <div className="max-w-7xl mx-auto px-5 py-24">Product not found. <Link to="/products" className="text-primary">Back to products</Link></div>;

  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-12 lg:py-16" data-testid="product-detail-page">
      <Link to="/products" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary transition-colors duration-200" data-testid="back-to-products">
        <ArrowLeft className="h-4 w-4 mr-1" /> All products
      </Link>
      <div className="mt-6 grid gap-10 lg:grid-cols-2">
        <Reveal>
          <div className="rounded-3xl overflow-hidden border border-border">
            <img src={p.image} alt={p.name} className="w-full aspect-square object-cover" />
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <div className="flex items-center gap-2">
            <Badge className="rounded-full">{p.category}</Badge>
            <Badge variant="secondary" className="rounded-full">{p.power}</Badge>
          </div>
          <h1 className="mt-4 font-display text-4xl font-extrabold tracking-tight">{p.name}</h1>
          <p className="mt-2 text-lg text-primary font-semibold">{p.tagline}</p>
          <p className="mt-4 text-muted-foreground leading-relaxed">{p.description}</p>
          <div className="mt-6 rounded-2xl bg-secondary/50 border border-border p-5">
            <p className="text-sm text-muted-foreground">Indicative price range</p>
            <p className="font-display text-2xl font-bold text-primary">{p.price_range}</p>
          </div>
          <h3 className="mt-8 font-display font-bold text-lg">Specifications</h3>
          <ul className="mt-3 space-y-2">
            {p.specs.map((s) => (
              <li key={s} className="flex items-start gap-2 text-sm">
                <Check className="h-5 w-5 text-primary shrink-0" /> <span>{s}</span>
              </li>
            ))}
          </ul>
          <QuoteDialog defaultProduct={p.name} title={`Enquire: ${p.name}`} trigger={
            <Button size="lg" className="mt-8 rounded-full h-13 px-8" data-testid="product-enquire-btn">
              <MessageCircle className="h-5 w-5 mr-2" /> Enquire about this product
            </Button>} />
        </Reveal>
      </div>
    </div>
  );
}
