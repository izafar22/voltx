import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { api, inr } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { LayoutDashboard, ShieldCheck, CalendarPlus, FileText, Receipt, Check, Loader2, Wrench, Clock } from "lucide-react";

const statusColors = {
  Requested: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  Scheduled: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  "In Progress": "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  Completed: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  pending: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  approved: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  declined: "bg-red-500/15 text-red-600 dark:text-red-400",
};

const Stat = ({ icon: Icon, label, value }) => (
  <Card className="rounded-2xl">
    <CardContent className="p-5 flex items-center gap-4">
      <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center"><Icon className="h-6 w-6 text-primary" /></div>
      <div><p className="text-sm text-muted-foreground">{label}</p><p className="font-display text-2xl font-bold">{value}</p></div>
    </CardContent>
  </Card>
);

function BookServiceForm({ onDone }) {
  const [serviceType, setServiceType] = useState("Repair");
  const { register, handleSubmit, reset, setValue, formState: { isSubmitting, errors } } = useForm();
  const submit = async (d) => {
    try {
      await api.post("/bookings", { ...d, service_type: serviceType });
      toast.success("Booking confirmed!", { description: "WhatsApp confirmation sent. We'll assign a technician soon." });
      reset(); onDone();
    } catch { toast.error("Could not book. Try again."); }
  };
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <div className="space-y-1.5">
        <Label>Service type</Label>
        <Select value={serviceType} onValueChange={setServiceType}>
          <SelectTrigger data-testid="booking-service-type" className="h-11"><SelectValue /></SelectTrigger>
          <SelectContent>{["Repair", "Installation", "Diagnostics", "AMC Visit"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="space-y-1.5"><Label>Date</Label><Input data-testid="booking-date" type="date" {...register("date", { required: true })} className="h-11" />{errors.date && <p className="text-xs text-destructive">Required</p>}</div>
        <div className="space-y-1.5">
          <Label>Time slot</Label>
          <Select onValueChange={(v) => setValue("slot", v, { shouldValidate: true })}>
            <SelectTrigger data-testid="booking-slot" className="h-11"><SelectValue placeholder="Select slot" /></SelectTrigger>
            <SelectContent>{["09:00–11:00", "11:00–13:00", "14:00–16:00", "16:00–18:00"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
          </Select>
          <input type="hidden" {...register("slot", { required: true })} />
          {errors.slot && <p className="text-xs text-destructive">Required</p>}
        </div>
      </div>
      <div className="space-y-1.5"><Label>Device (optional)</Label><Input data-testid="booking-device" {...register("device")} placeholder="e.g. RUSHX Home 7.4kW" className="h-11" /></div>
      <div className="space-y-1.5"><Label>Issue / description</Label><Textarea data-testid="booking-description" {...register("description", { required: true })} rows={3} placeholder="Describe the issue or requirement" />{errors.description && <p className="text-xs text-destructive">Required</p>}</div>
      <Button type="submit" disabled={isSubmitting} data-testid="booking-submit" className="w-full h-11 rounded-lg">
        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirm booking"}
      </Button>
    </form>
  );
}

export default function Portal() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [bookOpen, setBookOpen] = useState(false);

  const { data: bookings = [] } = useQuery({ queryKey: ["bookings"], queryFn: async () => (await api.get("/bookings")).data });
  const { data: sub = {} } = useQuery({ queryKey: ["sub"], queryFn: async () => (await api.get("/subscriptions/me")).data });
  const { data: plans = [] } = useQuery({ queryKey: ["plans"], queryFn: async () => (await api.get("/amc-plans")).data });
  const { data: quotes = [] } = useQuery({ queryKey: ["quotes"], queryFn: async () => (await api.get("/quotes")).data });
  const { data: invoices = [] } = useQuery({ queryKey: ["invoices"], queryFn: async () => (await api.get("/invoices")).data });

  const refresh = () => { qc.invalidateQueries(); setBookOpen(false); };

  const subscribe = async (planId) => {
    try { await api.post("/subscriptions", { plan_id: planId }); toast.success("AMC activated!", { description: "Payment processed (demo). Welcome message sent." }); qc.invalidateQueries(); }
    catch { toast.error("Subscription failed."); }
  };
  const cancelSub = async () => { await api.post("/subscriptions/cancel"); toast.success("AMC cancelled."); qc.invalidateQueries(); };
  const decideQuote = async (id, decision) => { await api.patch(`/quotes/${id}`, { decision }); toast.success(`Quote ${decision}.`); qc.invalidateQueries(); };

  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-10" data-testid="portal-page">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight">Hi, {user?.name?.split(" ")[0] || "there"} 👋</h1>
          <p className="text-muted-foreground">Manage your AMC, service visits and quotes.</p>
        </div>
        <Dialog open={bookOpen} onOpenChange={setBookOpen}>
          <DialogTrigger asChild><Button className="rounded-full" data-testid="open-booking-btn"><CalendarPlus className="h-4 w-4 mr-2" /> Book a service</Button></DialogTrigger>
          <DialogContent data-testid="booking-dialog"><DialogHeader><DialogTitle className="font-display text-2xl">Book a service visit</DialogTitle></DialogHeader><BookServiceForm onDone={refresh} /></DialogContent>
        </Dialog>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={ShieldCheck} label="Active AMC" value={sub?.plan_name || "None"} />
        <Stat icon={Wrench} label="Service requests" value={bookings.length} />
        <Stat icon={FileText} label="Pending quotes" value={quotes.filter((q) => q.status === "pending").length} />
        <Stat icon={Receipt} label="Invoices" value={invoices.length} />
      </motion.div>

      <Tabs defaultValue="overview" className="mt-8">
        <TabsList className="flex-wrap h-auto" data-testid="portal-tabs">
          <TabsTrigger value="overview" data-testid="tab-overview"><LayoutDashboard className="h-4 w-4 mr-1.5" /> Overview</TabsTrigger>
          <TabsTrigger value="amc" data-testid="tab-amc"><ShieldCheck className="h-4 w-4 mr-1.5" /> AMC Plans</TabsTrigger>
          <TabsTrigger value="quotes" data-testid="tab-quotes"><FileText className="h-4 w-4 mr-1.5" /> Quotes</TabsTrigger>
          <TabsTrigger value="invoices" data-testid="tab-invoices"><Receipt className="h-4 w-4 mr-1.5" /> Invoices</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <Card className="rounded-2xl">
            <CardHeader><CardTitle className="font-display">Service requests</CardTitle></CardHeader>
            <CardContent>
              {bookings.length === 0 ? <p className="text-muted-foreground text-sm py-8 text-center">No service requests yet. Book your first visit above.</p> : (
                <div className="space-y-3" data-testid="bookings-list">
                  {bookings.map((b) => (
                    <div key={b.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4">
                      <div>
                        <div className="flex items-center gap-2"><span className="font-semibold">{b.service_type}</span><Badge className={`rounded-full border-0 ${statusColors[b.status]}`}>{b.status}</Badge></div>
                        <p className="text-sm text-muted-foreground mt-1 flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {b.date} · {b.slot} {b.device && `· ${b.device}`}</p>
                        <p className="text-sm text-muted-foreground">{b.description}</p>
                      </div>
                      {b.technician && <span className="text-sm text-muted-foreground">Tech: <b>{b.technician}</b></span>}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="amc" className="mt-6">
          {sub?.id && (
            <Card className="rounded-2xl mb-6 border-primary/40">
              <CardContent className="p-6 flex flex-wrap items-center justify-between gap-4">
                <div><p className="text-sm text-muted-foreground">Current plan</p><p className="font-display text-2xl font-bold text-primary">{sub.plan_name} AMC</p><p className="text-sm text-muted-foreground">Next billing: {new Date(sub.next_billing).toLocaleDateString("en-IN")}</p></div>
                <Button variant="outline" onClick={cancelSub} data-testid="cancel-amc-btn">Cancel AMC</Button>
              </CardContent>
            </Card>
          )}
          <div className="grid gap-6 md:grid-cols-3">
            {plans.map((p) => (
              <Card key={p.id} className={`rounded-2xl relative ${p.popular ? "border-primary shadow-lg shadow-primary/10" : ""}`} data-testid={`amc-plan-${p.name}`}>
                {p.popular && <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full">Most popular</Badge>}
                <CardHeader><CardTitle className="font-display text-xl">{p.name}</CardTitle><p className="text-sm text-muted-foreground">{p.tagline}</p></CardHeader>
                <CardContent>
                  <p className="font-display text-3xl font-extrabold">{inr(p.price)}<span className="text-base font-normal text-muted-foreground">/{p.period}</span></p>
                  <ul className="mt-5 space-y-2">{p.features.map((f) => <li key={f} className="flex items-start gap-2 text-sm"><Check className="h-5 w-5 text-primary shrink-0" /> {f}</li>)}</ul>
                  <Button onClick={() => subscribe(p.id)} disabled={sub?.plan_id === p.id} className="w-full mt-6 rounded-lg" variant={p.popular ? "default" : "outline"} data-testid={`subscribe-${p.name}`}>
                    {sub?.plan_id === p.id ? "Current plan" : "Subscribe"}
                  </Button>
                  <p className="text-xs text-center text-muted-foreground mt-2">Recurring via Razorpay (demo)</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="quotes" className="mt-6">
          <Card className="rounded-2xl"><CardContent className="p-6">
            {quotes.length === 0 ? <p className="text-muted-foreground text-sm py-8 text-center">No quotes yet. When RUSHX sends you a custom quote, it appears here.</p> : (
              <div className="space-y-3" data-testid="quotes-list">
                {quotes.map((q) => (
                  <div key={q.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4">
                    <div><div className="flex items-center gap-2"><span className="font-semibold">{q.title}</span><Badge className={`rounded-full border-0 ${statusColors[q.status]}`}>{q.status}</Badge></div><p className="text-sm text-muted-foreground">{q.details}</p><p className="font-display font-bold text-primary mt-1">{inr(q.amount)}</p></div>
                    {q.status === "pending" && <div className="flex gap-2"><Button size="sm" onClick={() => decideQuote(q.id, "approved")} data-testid={`approve-quote-${q.id}`}>Approve</Button><Button size="sm" variant="outline" onClick={() => decideQuote(q.id, "declined")} data-testid={`decline-quote-${q.id}`}>Decline</Button></div>}
                  </div>
                ))}
              </div>
            )}
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="invoices" className="mt-6">
          <Card className="rounded-2xl"><CardContent className="p-6">
            {invoices.length === 0 ? <p className="text-muted-foreground text-sm py-8 text-center">No invoices yet.</p> : (
              <div className="space-y-3" data-testid="invoices-list">
                {invoices.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between rounded-xl border border-border p-4">
                    <div><p className="font-semibold">{inv.plan_name} AMC</p><p className="text-sm text-muted-foreground">{new Date(inv.created_at).toLocaleDateString("en-IN")}</p></div>
                    <div className="text-right"><p className="font-display font-bold">{inr(inv.amount)}</p><Badge className="rounded-full border-0 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">{inv.status}</Badge></div>
                  </div>
                ))}
              </div>
            )}
          </CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
