import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Reveal } from "@/components/shared/Reveal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { MapPin, Mail, Phone, MessageCircle, Loader2 } from "lucide-react";

export default function Contact() {
  const { register, handleSubmit, reset, formState: { isSubmitting, errors } } = useForm();
  const onSubmit = async (data) => {
    try {
      await api.post("/leads", { ...data, segment: "Residential", source: "contact-page" });
      toast.success("Message sent!", { description: "WhatsApp acknowledgment sent. We'll reach out within 24 hours." });
      reset();
    } catch { toast.error("Could not send. Please try again."); }
  };

  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-24 grid gap-12 lg:grid-cols-2" data-testid="contact-page">
      <Reveal>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Get in touch</p>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl font-extrabold tracking-tighter">Let's talk energy</h1>
        <p className="mt-4 text-muted-foreground max-w-md">Tell us about your requirement — home, business, fleet or government. We respond within 24 hours with a tailored quote.</p>
        <div className="mt-10 space-y-5">
          {[{ icon: MapPin, t: "Head office", d: "Pune, Maharashtra, India" }, { icon: Phone, t: "Call us", d: "+91 98765 43210" }, { icon: Mail, t: "Email", d: "hello@rushx.in" }].map((c) => (
            <div key={c.t} className="flex items-start gap-4">
              <div className="h-11 w-11 rounded-xl bg-primary/10 flex items-center justify-center shrink-0"><c.icon className="h-5 w-5 text-primary" /></div>
              <div><p className="font-semibold">{c.t}</p><p className="text-muted-foreground text-sm">{c.d}</p></div>
            </div>
          ))}
        </div>
      </Reveal>
      <Reveal delay={0.1}>
        <form onSubmit={handleSubmit(onSubmit)} className="rounded-3xl border border-border bg-card p-8 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5"><Label>Name</Label><Input data-testid="contact-name" {...register("name", { required: true })} className="h-11" placeholder="Your name" />{errors.name && <p className="text-xs text-destructive">Required</p>}</div>
            <div className="space-y-1.5"><Label>Phone</Label><Input data-testid="contact-phone" {...register("phone", { required: true })} className="h-11" placeholder="+91" />{errors.phone && <p className="text-xs text-destructive">Required</p>}</div>
          </div>
          <div className="space-y-1.5"><Label>Email</Label><Input data-testid="contact-email" type="email" {...register("email", { required: true })} className="h-11" placeholder="you@email.com" />{errors.email && <p className="text-xs text-destructive">Required</p>}</div>
          <div className="space-y-1.5"><Label>Company (optional)</Label><Input data-testid="contact-company" {...register("company")} className="h-11" placeholder="Company" /></div>
          <div className="space-y-1.5"><Label>Message</Label><Textarea data-testid="contact-message" {...register("message", { required: true })} rows={4} placeholder="How can we help?" />{errors.message && <p className="text-xs text-destructive">Required</p>}</div>
          <Button type="submit" disabled={isSubmitting} data-testid="contact-submit" className="w-full h-12 rounded-lg">
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><MessageCircle className="h-4 w-4 mr-2" /> Send message</>}
          </Button>
        </form>
      </Reveal>
    </div>
  );
}
