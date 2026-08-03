import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, inr } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Inbox, Users, CalendarCheck, ShieldCheck, IndianRupee, MessageSquare, TrendingUp } from "lucide-react";

const leadStatuses = ["New", "Contacted", "Quoted", "Won", "Lost"];
const bookingStatuses = ["Requested", "Scheduled", "In Progress", "Completed"];
const badge = { New: "bg-amber-500/15 text-amber-600", Contacted: "bg-sky-500/15 text-sky-600", Quoted: "bg-blue-500/15 text-blue-600", Won: "bg-emerald-500/15 text-emerald-600", Lost: "bg-red-500/15 text-red-600", Requested: "bg-amber-500/15 text-amber-600", Scheduled: "bg-sky-500/15 text-sky-600", "In Progress": "bg-blue-500/15 text-blue-600", Completed: "bg-emerald-500/15 text-emerald-600", active: "bg-emerald-500/15 text-emerald-600", cancelled: "bg-red-500/15 text-red-600" };

const KPI = ({ icon: Icon, label, value }) => (
  <Card className="rounded-2xl"><CardContent className="p-5"><div className="flex items-center justify-between"><span className="text-sm text-muted-foreground">{label}</span><Icon className="h-5 w-5 text-primary" /></div><p className="font-display text-3xl font-extrabold mt-2">{value}</p></CardContent></Card>
);

function QuoteDialogAdmin({ lead, customers, onDone }) {
  const [open, setOpen] = useState(false);
  const [userId, setUserId] = useState("");
  const [form, setForm] = useState({ title: "", amount: "", details: "" });
  const submit = async () => {
    if (!userId || !form.title || !form.amount) { toast.error("Fill customer, title and amount."); return; }
    try {
      await api.post("/admin/quotes", { user_id: userId, lead_id: lead?.id || "", title: form.title, amount: Number(form.amount), details: form.details });
      toast.success("Quote sent to customer portal."); setOpen(false); onDone();
    } catch { toast.error("Failed to send quote."); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="outline" data-testid="send-quote-btn">Send quote</Button></DialogTrigger>
      <DialogContent data-testid="admin-quote-dialog">
        <DialogHeader><DialogTitle className="font-display text-2xl">Send a quote</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5"><Label>Customer</Label>
            <Select value={userId} onValueChange={setUserId}><SelectTrigger data-testid="quote-customer" className="h-11"><SelectValue placeholder="Select customer" /></SelectTrigger>
              <SelectContent>{customers.map((c) => <SelectItem key={c.user_id} value={c.user_id}>{c.name} ({c.email})</SelectItem>)}</SelectContent></Select>
            <p className="text-xs text-muted-foreground">Customer must have signed in at least once.</p>
          </div>
          <div className="space-y-1.5"><Label>Title</Label><Input data-testid="quote-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. 7.4kW install + wiring" className="h-11" /></div>
          <div className="space-y-1.5"><Label>Amount (₹)</Label><Input data-testid="quote-amount" type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="45000" className="h-11" /></div>
          <div className="space-y-1.5"><Label>Details</Label><Textarea data-testid="quote-details" value={form.details} onChange={(e) => setForm({ ...form, details: e.target.value })} rows={3} /></div>
          <Button onClick={submit} className="w-full h-11 rounded-lg" data-testid="quote-send-submit">Send quote</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Admin() {
  const qc = useQueryClient();
  const { data: stats = {} } = useQuery({ queryKey: ["stats"], queryFn: async () => (await api.get("/admin/stats")).data });
  const { data: leads = [] } = useQuery({ queryKey: ["a-leads"], queryFn: async () => (await api.get("/admin/leads")).data });
  const { data: bookings = [] } = useQuery({ queryKey: ["a-bookings"], queryFn: async () => (await api.get("/admin/bookings")).data });
  const { data: subs = [] } = useQuery({ queryKey: ["a-subs"], queryFn: async () => (await api.get("/admin/subscriptions")).data });
  const { data: customers = [] } = useQuery({ queryKey: ["a-cust"], queryFn: async () => (await api.get("/admin/customers")).data });
  const { data: messages = [] } = useQuery({ queryKey: ["a-msgs"], queryFn: async () => (await api.get("/admin/messages")).data });

  const setLeadStatus = async (id, status) => { await api.patch(`/admin/leads/${id}`, { status }); qc.invalidateQueries({ queryKey: ["a-leads"] }); qc.invalidateQueries({ queryKey: ["stats"] }); };
  const updateBooking = async (id, patch) => { await api.patch(`/admin/bookings/${id}`, patch); qc.invalidateQueries({ queryKey: ["a-bookings"] }); toast.success("Booking updated."); };

  const pipeline = leadStatuses.map((s) => ({ name: s, count: leads.filter((l) => l.status === s).length }));

  return (
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-10" data-testid="admin-page">
      <h1 className="font-display text-3xl font-extrabold tracking-tight">Admin dashboard</h1>
      <p className="text-muted-foreground">Operations overview — leads, bookings, AMC and payments.</p>

      <div className="mt-8 grid gap-4 grid-cols-2 lg:grid-cols-4">
        <KPI icon={Inbox} label="Total leads" value={stats.leads ?? 0} />
        <KPI icon={TrendingUp} label="New leads" value={stats.new_leads ?? 0} />
        <KPI icon={CalendarCheck} label="Bookings" value={stats.bookings ?? 0} />
        <KPI icon={ShieldCheck} label="Active AMC" value={stats.active_subscriptions ?? 0} />
        <KPI icon={Users} label="Customers" value={stats.customers ?? 0} />
        <KPI icon={IndianRupee} label="AMC revenue" value={inr(stats.revenue ?? 0)} />
      </div>

      <Tabs defaultValue="leads" className="mt-8">
        <TabsList className="flex-wrap h-auto" data-testid="admin-tabs">
          <TabsTrigger value="leads" data-testid="atab-leads"><Inbox className="h-4 w-4 mr-1.5" /> Leads</TabsTrigger>
          <TabsTrigger value="bookings" data-testid="atab-bookings"><CalendarCheck className="h-4 w-4 mr-1.5" /> Bookings</TabsTrigger>
          <TabsTrigger value="subs" data-testid="atab-subs"><ShieldCheck className="h-4 w-4 mr-1.5" /> AMC</TabsTrigger>
          <TabsTrigger value="customers" data-testid="atab-customers"><Users className="h-4 w-4 mr-1.5" /> Customers</TabsTrigger>
          <TabsTrigger value="messages" data-testid="atab-messages"><MessageSquare className="h-4 w-4 mr-1.5" /> WhatsApp</TabsTrigger>
        </TabsList>

        <TabsContent value="leads" className="mt-6 space-y-6">
          <Card className="rounded-2xl"><CardHeader><CardTitle className="font-display">Lead pipeline</CardTitle></CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pipeline}><CartesianGrid strokeDasharray="3 3" opacity={0.2} /><XAxis dataKey="name" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip contentStyle={{ borderRadius: 12, backdropFilter: "blur(8px)" }} /><Bar dataKey="count" fill="#16A34A" radius={[6, 6, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card className="rounded-2xl"><CardHeader><CardTitle className="font-display">Leads inbox</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
              <Table data-testid="leads-table"><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Contact</TableHead><TableHead>Segment</TableHead><TableHead>Product</TableHead><TableHead>Status</TableHead><TableHead>Action</TableHead></TableRow></TableHeader>
                <TableBody>{leads.length === 0 ? <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">No leads yet.</TableCell></TableRow> : leads.map((l) => (
                  <TableRow key={l.id} data-testid={`lead-row-${l.id}`}>
                    <TableCell className="font-medium">{l.name}<div className="text-xs text-muted-foreground max-w-[200px] truncate">{l.message}</div></TableCell>
                    <TableCell className="text-sm">{l.phone}<div className="text-xs text-muted-foreground">{l.email}</div></TableCell>
                    <TableCell><Badge variant="secondary" className="rounded-full">{l.segment}</Badge></TableCell>
                    <TableCell className="text-sm">{l.product || "—"}</TableCell>
                    <TableCell><Select value={l.status} onValueChange={(v) => setLeadStatus(l.id, v)}><SelectTrigger className="h-9 w-32" data-testid={`lead-status-${l.id}`}><SelectValue /></SelectTrigger><SelectContent>{leadStatuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></TableCell>
                    <TableCell><QuoteDialogAdmin lead={l} customers={customers} onDone={() => qc.invalidateQueries()} /></TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="bookings" className="mt-6">
          <Card className="rounded-2xl"><CardHeader><CardTitle className="font-display">Service bookings</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
              <Table data-testid="admin-bookings-table"><TableHeader><TableRow><TableHead>Customer</TableHead><TableHead>Service</TableHead><TableHead>Slot</TableHead><TableHead>Technician</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
                <TableBody>{bookings.length === 0 ? <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-8">No bookings.</TableCell></TableRow> : bookings.map((b) => (
                  <TableRow key={b.id} data-testid={`admin-booking-${b.id}`}>
                    <TableCell className="font-medium">{b.customer_name}<div className="text-xs text-muted-foreground">{b.customer_email}</div></TableCell>
                    <TableCell>{b.service_type}<div className="text-xs text-muted-foreground max-w-[180px] truncate">{b.description}</div></TableCell>
                    <TableCell className="text-sm">{b.date}<div className="text-xs text-muted-foreground">{b.slot}</div></TableCell>
                    <TableCell><Input defaultValue={b.technician} placeholder="Assign..." className="h-9 w-32" data-testid={`tech-input-${b.id}`} onBlur={(e) => e.target.value !== b.technician && updateBooking(b.id, { technician: e.target.value })} /></TableCell>
                    <TableCell><Select value={b.status} onValueChange={(v) => updateBooking(b.id, { status: v })}><SelectTrigger className="h-9 w-36" data-testid={`booking-status-${b.id}`}><SelectValue /></SelectTrigger><SelectContent>{bookingStatuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="subs" className="mt-6">
          <Card className="rounded-2xl"><CardContent className="p-6 overflow-x-auto">
            <Table data-testid="subs-table"><TableHeader><TableRow><TableHead>Customer</TableHead><TableHead>Plan</TableHead><TableHead>Amount</TableHead><TableHead>Next billing</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
              <TableBody>{subs.length === 0 ? <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-8">No subscribers.</TableCell></TableRow> : subs.map((s) => (
                <TableRow key={s.id}><TableCell className="font-medium">{s.customer_name}<div className="text-xs text-muted-foreground">{s.customer_email}</div></TableCell><TableCell>{s.plan_name}</TableCell><TableCell>{inr(s.amount)}</TableCell><TableCell className="text-sm">{new Date(s.next_billing).toLocaleDateString("en-IN")}</TableCell><TableCell><Badge className={`rounded-full border-0 ${badge[s.status]}`}>{s.status}</Badge></TableCell></TableRow>
              ))}</TableBody>
            </Table>
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="customers" className="mt-6">
          <Card className="rounded-2xl"><CardContent className="p-6 overflow-x-auto">
            <Table data-testid="customers-table"><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Joined</TableHead></TableRow></TableHeader>
              <TableBody>{customers.length === 0 ? <TableRow><TableCell colSpan={3} className="text-center text-muted-foreground py-8">No customers yet.</TableCell></TableRow> : customers.map((c) => (
                <TableRow key={c.user_id}><TableCell className="font-medium">{c.name}</TableCell><TableCell className="text-sm">{c.email}</TableCell><TableCell className="text-sm">{new Date(c.created_at).toLocaleDateString("en-IN")}</TableCell></TableRow>
              ))}</TableBody>
            </Table>
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="messages" className="mt-6">
          <Card className="rounded-2xl"><CardHeader><CardTitle className="font-display">WhatsApp message log</CardTitle><p className="text-sm text-muted-foreground">Automated acknowledgments & confirmations (Twilio — DEMO/MOCKED).</p></CardHeader>
            <CardContent className="space-y-3" data-testid="messages-list">
              {messages.length === 0 ? <p className="text-center text-muted-foreground py-8">No messages yet.</p> : messages.map((m) => (
                <div key={m.id} className="rounded-xl border border-border p-4"><div className="flex items-center justify-between"><Badge variant="secondary" className="rounded-full"><MessageSquare className="h-3 w-3 mr-1" /> {m.channel}</Badge><span className="text-xs text-muted-foreground">{new Date(m.created_at).toLocaleString("en-IN")}</span></div><p className="text-sm mt-2">{m.body}</p><p className="text-xs text-muted-foreground mt-1">To: {m.to}</p></div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
