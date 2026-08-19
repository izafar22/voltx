import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import {
  LayoutDashboard, Cpu, Users, AlertTriangle, Banknote, IndianRupee, Zap, Wifi, WifiOff,
  RotateCw, Plus, Thermometer, Activity, Loader2,
} from "lucide-react";
import { api, inr, inr0 } from "@/lib/api";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";

const statusBadge = {
  Available: "bg-charging/15 text-charging", Charging: "bg-amber-500/15 text-amber-500",
  Offline: "bg-muted text-muted-foreground", Fault: "bg-destructive/15 text-destructive",
};

const KPI = ({ icon: Icon, label, value, accent }) => (
  <div className="rounded-xl border border-border/60 p-5">
    <div className="flex items-center justify-between"><span className="text-xs uppercase tracking-widest text-muted-foreground">{label}</span><Icon className={`h-4.5 w-4.5 ${accent || "text-muted-foreground"}`} strokeWidth={1.5} /></div>
    <p className="font-mono text-3xl font-light tabular mt-2">{value}</p>
  </div>
);

export default function AdminDashboard() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("overview");

  const { data: summary = {} } = useQuery({ queryKey: ["asum"], queryFn: async () => (await api.get("/admin/summary")).data });
  const { data: chargers = [] } = useQuery({ queryKey: ["achargers"], queryFn: async () => (await api.get("/admin/chargers")).data, refetchInterval: tab === "chargers" ? 5000 : false });
  const { data: owners = [] } = useQuery({ queryKey: ["aowners"], queryFn: async () => (await api.get("/admin/owners")).data });
  const { data: customers = [] } = useQuery({ queryKey: ["acust"], queryFn: async () => (await api.get("/admin/users")).data });
  const { data: faults = [] } = useQuery({ queryKey: ["afaults"], queryFn: async () => (await api.get("/admin/faults")).data });
  const { data: withdrawals = [] } = useQuery({ queryKey: ["awd"], queryFn: async () => (await api.get("/admin/withdrawals")).data });

  const nav = [
    { label: "Overview", icon: LayoutDashboard, active: tab === "overview", onClick: () => setTab("overview") },
    { label: "Chargers", icon: Cpu, active: tab === "chargers", onClick: () => setTab("chargers") },
    { label: "Network", icon: Users, active: tab === "network", onClick: () => setTab("network") },
    { label: "Faults", icon: AlertTriangle, active: tab === "faults", onClick: () => setTab("faults") },
    { label: "Payouts", icon: Banknote, active: tab === "payouts", onClick: () => setTab("payouts") },
  ];

  const restart = async (id) => { await api.post(`/admin/chargers/${id}/restart`); toast.success(`${id} restarted`); qc.invalidateQueries({ queryKey: ["achargers"] }); qc.invalidateQueries({ queryKey: ["afaults"] }); };
  const setStatus = async (id, status) => { await api.post(`/admin/chargers/${id}/status`, { status }); toast.success(`${id} → ${status}`); qc.invalidateQueries({ queryKey: ["achargers"] }); };
  const updateWd = async (id, status) => { await api.patch(`/admin/withdrawals/${id}`, { status }); toast.success(`Withdrawal ${status}`); qc.invalidateQueries({ queryKey: ["awd"] }); };

  const pie = [
    { name: "Online", value: summary.online || 0, color: "hsl(var(--charging))" },
    { name: "Offline", value: summary.offline || 0, color: "hsl(var(--muted-foreground))" },
    { name: "Fault", value: summary.faults || 0, color: "hsl(var(--destructive))" },
  ];

  return (
    <DashboardShell nav={nav} title="Network Admin">
      {tab === "overview" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6" data-testid="admin-overview">
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            <KPI icon={IndianRupee} label="Total revenue" value={inr0(summary.total_revenue)} accent="text-charging" />
            <KPI icon={Banknote} label="Company commission (10%)" value={inr0(summary.commission)} accent="text-wallet" />
            <KPI icon={Zap} label="Units sold" value={`${summary.units_sold ?? 0}`} />
            <KPI icon={Activity} label="Sessions" value={summary.total_sessions ?? 0} />
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="rounded-xl lg:col-span-1"><CardHeader><CardTitle className="font-display text-base">Charger health</CardTitle></CardHeader>
              <CardContent className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={3}>{pie.map((e, i) => <Cell key={i} fill={e.color} />)}</Pie><Tooltip contentStyle={{ borderRadius: 10, background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))" }} /><Legend /></PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <div className="lg:col-span-2 grid grid-cols-2 gap-4 content-start">
              <KPI icon={Wifi} label="Online" value={summary.online ?? 0} accent="text-charging" />
              <KPI icon={WifiOff} label="Offline" value={summary.offline ?? 0} />
              <KPI icon={AlertTriangle} label="Faults" value={summary.faults ?? 0} accent="text-destructive" />
              <KPI icon={Banknote} label="Owner payouts (90%)" value={inr0(summary.owner_payouts)} accent="text-charging" />
              <KPI icon={Users} label="Customers" value={summary.customers ?? 0} />
              <KPI icon={Cpu} label="Chargers" value={summary.chargers_total ?? 0} />
            </div>
          </div>
        </motion.div>
      )}

      {tab === "chargers" && (
        <div className="space-y-4" data-testid="admin-chargers">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Live monitoring · auto-refresh 5s</p>
            <AddChargerDialog owners={owners} onDone={() => qc.invalidateQueries({ queryKey: ["achargers"] })} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {chargers.map((c) => (
              <div key={c.charger_id} className="rounded-xl border border-border/60 p-5" data-testid={`charger-card-${c.charger_id}`}>
                <div className="flex items-start justify-between">
                  <div><p className="font-mono text-xs text-muted-foreground">{c.charger_id}</p><h3 className="font-medium mt-0.5">{c.name}</h3><p className="text-xs text-muted-foreground">{c.owner_name} · {c.location}</p></div>
                  <Badge className={`rounded-full ${statusBadge[c.status]}`}>{c.status}</Badge>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-y-1.5 text-sm font-mono">
                  <span className="text-muted-foreground font-sans text-xs">Voltage</span><span className="text-right">{c.voltage} V</span>
                  <span className="text-muted-foreground font-sans text-xs">Current</span><span className="text-right">{c.current} A</span>
                  <span className="text-muted-foreground font-sans text-xs">Power</span><span className="text-right">{c.power_kw} kW</span>
                  <span className="text-muted-foreground font-sans text-xs">Energy today</span><span className="text-right">{c.energy_today} kWh</span>
                  <span className="text-muted-foreground font-sans text-xs flex items-center gap-1"><Thermometer className="h-3 w-3" />Temp</span><span className="text-right">{c.temperature}°C</span>
                  <span className="text-muted-foreground font-sans text-xs">Signal</span><span className="text-right">{c.online ? `${c.signal}/5` : "—"}</span>
                  <span className="text-muted-foreground font-sans text-xs">Firmware</span><span className="text-right">{c.firmware}</span>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => restart(c.charger_id)} data-testid={`restart-${c.charger_id}`} className="flex-1"><RotateCw className="h-3.5 w-3.5 mr-1" /> Restart</Button>
                  <Select value={c.status} onValueChange={(v) => setStatus(c.charger_id, v)}>
                    <SelectTrigger className="h-9 w-28" data-testid={`status-${c.charger_id}`}><SelectValue /></SelectTrigger>
                    <SelectContent>{["Available", "Offline", "Fault"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "network" && (
        <div className="space-y-8" data-testid="admin-network">
          <div>
            <div className="flex items-center justify-between mb-3"><h2 className="font-display text-lg font-semibold">Charger owners</h2><AddOwnerDialog onDone={() => qc.invalidateQueries({ queryKey: ["aowners"] })} /></div>
            <Card className="rounded-xl"><CardContent className="p-0 overflow-x-auto">
              <Table data-testid="owners-table"><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Phone</TableHead><TableHead>Chargers</TableHead><TableHead className="text-right">Wallet</TableHead></TableRow></TableHeader>
                <TableBody>{owners.map((o) => <TableRow key={o.user_id}><TableCell className="font-medium">{o.name}</TableCell><TableCell className="font-mono text-sm">{o.phone}</TableCell><TableCell>{o.chargers}</TableCell><TableCell className="text-right font-mono">{inr(o.wallet)}</TableCell></TableRow>)}</TableBody>
              </Table>
            </CardContent></Card>
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold mb-3">Customers</h2>
            <Card className="rounded-xl"><CardContent className="p-0 overflow-x-auto">
              <Table data-testid="customers-table"><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Phone</TableHead><TableHead className="text-right">Wallet</TableHead><TableHead className="text-right">Action</TableHead></TableRow></TableHeader>
                <TableBody>{customers.length === 0 ? <TableRow><TableCell colSpan={4} className="text-center text-muted-foreground py-6">No customers yet.</TableCell></TableRow> : customers.map((u) => <TableRow key={u.user_id}><TableCell className="font-medium">{u.name}</TableCell><TableCell className="font-mono text-sm">{u.phone}</TableCell><TableCell className="text-right font-mono">{inr(u.wallet)}</TableCell><TableCell className="text-right"><WalletAdjustDialog user={u} onDone={() => qc.invalidateQueries({ queryKey: ["acust"] })} /></TableCell></TableRow>)}</TableBody>
              </Table>
            </CardContent></Card>
          </div>
        </div>
      )}

      {tab === "faults" && (
        <Card className="rounded-xl" data-testid="admin-faults"><CardHeader><CardTitle className="font-display text-base">Fault logs</CardTitle></CardHeader>
          <CardContent>
            {faults.length === 0 ? <p className="text-sm text-muted-foreground">No faults logged.</p> : (
              <div className="space-y-2">{faults.map((f) => (
                <div key={f.id} className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className={`h-5 w-5 ${f.severity === "critical" ? "text-destructive" : "text-muted-foreground"}`} />
                    <div><p className="text-sm font-medium">{f.message}</p><p className="text-xs text-muted-foreground font-mono">{f.charger_id} · {new Date(f.created_at).toLocaleString("en-IN")}</p></div>
                  </div>
                  <Badge className={f.resolved ? "bg-charging/15 text-charging" : "bg-destructive/15 text-destructive"}>{f.resolved ? "Resolved" : "Open"}</Badge>
                </div>
              ))}</div>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "payouts" && (
        <Card className="rounded-xl" data-testid="admin-payouts"><CardHeader><CardTitle className="font-display text-base">Owner withdrawal requests</CardTitle></CardHeader>
          <CardContent className="p-0 overflow-x-auto">
            <Table><TableHeader><TableRow><TableHead>Owner</TableHead><TableHead>Amount</TableHead><TableHead>Date</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Action</TableHead></TableRow></TableHeader>
              <TableBody>{withdrawals.length === 0 ? <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-6">No withdrawal requests.</TableCell></TableRow> : withdrawals.map((w) => (
                <TableRow key={w.id}><TableCell className="font-medium">{w.owner_name}</TableCell><TableCell className="font-mono">{inr(w.amount)}</TableCell><TableCell className="text-sm">{new Date(w.created_at).toLocaleDateString("en-IN")}</TableCell><TableCell><Badge variant="secondary" className="capitalize">{w.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    {w.status === "requested" && <div className="flex gap-2 justify-end"><Button size="sm" onClick={() => updateWd(w.id, "completed")} data-testid={`approve-wd-${w.id}`}>Complete</Button><Button size="sm" variant="outline" onClick={() => updateWd(w.id, "rejected")} data-testid={`reject-wd-${w.id}`}>Reject</Button></div>}
                  </TableCell>
                </TableRow>
              ))}</TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </DashboardShell>
  );
}

function AddChargerDialog({ owners, onDone }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", owner_id: "", connector: "Type 2", price_per_kwh: "15", max_power_kw: "7.4", location: "" });
  const submit = async () => {
    if (!f.name || !f.owner_id) { toast.error("Name and owner required"); return; }
    try {
      await api.post("/admin/chargers", { ...f, price_per_kwh: Number(f.price_per_kwh), max_power_kw: Number(f.max_power_kw) });
      toast.success("Charger added"); setOpen(false); onDone();
    } catch { toast.error("Failed"); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" data-testid="add-charger-btn"><Plus className="h-4 w-4 mr-1" /> Add charger</Button></DialogTrigger>
      <DialogContent data-testid="add-charger-dialog">
        <DialogHeader><DialogTitle className="font-display">Add charger</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5"><Label>Name</Label><Input data-testid="charger-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="h-11" /></div>
          <div className="space-y-1.5"><Label>Owner</Label>
            <Select value={f.owner_id} onValueChange={(v) => setF({ ...f, owner_id: v })}><SelectTrigger data-testid="charger-owner" className="h-11"><SelectValue placeholder="Select owner" /></SelectTrigger>
              <SelectContent>{owners.map((o) => <SelectItem key={o.user_id} value={o.user_id}>{o.name}</SelectItem>)}</SelectContent></Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Price/kWh</Label><Input data-testid="charger-price" type="number" value={f.price_per_kwh} onChange={(e) => setF({ ...f, price_per_kwh: e.target.value })} className="h-11" /></div>
            <div className="space-y-1.5"><Label>Max power (kW)</Label><Input data-testid="charger-power" type="number" value={f.max_power_kw} onChange={(e) => setF({ ...f, max_power_kw: e.target.value })} className="h-11" /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Connector</Label>
              <Select value={f.connector} onValueChange={(v) => setF({ ...f, connector: v })}><SelectTrigger className="h-11"><SelectValue /></SelectTrigger><SelectContent>{["Type 2", "CCS2", "CHAdeMO", "Bharat AC-001"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent></Select>
            </div>
            <div className="space-y-1.5"><Label>Location</Label><Input data-testid="charger-location" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} className="h-11" /></div>
          </div>
        </div>
        <DialogFooter><Button onClick={submit} data-testid="charger-submit" className="rounded-lg">Add charger</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddOwnerDialog({ onDone }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", phone: "" });
  const submit = async () => {
    if (!f.name || !f.phone) { toast.error("Name and phone required"); return; }
    try { await api.post("/admin/owners", f); toast.success("Owner added"); setOpen(false); setF({ name: "", phone: "" }); onDone(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="outline" data-testid="add-owner-btn"><Plus className="h-4 w-4 mr-1" /> Add owner</Button></DialogTrigger>
      <DialogContent data-testid="add-owner-dialog">
        <DialogHeader><DialogTitle className="font-display">Add owner</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5"><Label>Name</Label><Input data-testid="owner-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="h-11" /></div>
          <div className="space-y-1.5"><Label>Phone</Label><Input data-testid="owner-phone" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} placeholder="+91..." className="h-11 font-mono" /></div>
        </div>
        <DialogFooter><Button onClick={submit} data-testid="owner-submit" className="rounded-lg">Add owner</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function WalletAdjustDialog({ user, onDone }) {
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("");
  const submit = async () => {
    const v = Number(amount);
    if (!v) { toast.error("Enter amount"); return; }
    try { await api.post("/admin/wallet/adjust", { user_id: user.user_id, amount: v }); toast.success("Wallet adjusted"); setOpen(false); setAmount(""); onDone(); }
    catch { toast.error("Failed"); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="outline" data-testid={`adjust-${user.user_id}`}>Adjust</Button></DialogTrigger>
      <DialogContent data-testid="adjust-dialog">
        <DialogHeader><DialogTitle className="font-display">Adjust wallet — {user.name}</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">Positive to credit, negative to debit.</p>
        <Input data-testid="adjust-amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="e.g. 500 or -200" className="h-12 font-mono" />
        <DialogFooter><Button onClick={submit} data-testid="adjust-submit" className="rounded-lg">Apply</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
