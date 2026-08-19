import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { LayoutDashboard, Plug, Banknote, IndianRupee, Zap, Wallet, TrendingUp, Loader2, ArrowUpRight, ArrowDownLeft } from "lucide-react";
import { api, inr, inr0 } from "@/lib/api";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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

export default function OwnerDashboard() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("overview");
  const [amount, setAmount] = useState("");
  const [wdOpen, setWdOpen] = useState(false);

  const { data: summary = {} } = useQuery({ queryKey: ["osum"], queryFn: async () => (await api.get("/owner/summary")).data });
  const { data: chargers = [] } = useQuery({ queryKey: ["ochargers"], queryFn: async () => (await api.get("/owner/chargers")).data });
  const { data: txns = [] } = useQuery({ queryKey: ["otxns"], queryFn: async () => (await api.get("/owner/transactions")).data });
  const { data: withdrawals = [] } = useQuery({ queryKey: ["owd"], queryFn: async () => (await api.get("/owner/withdrawals")).data });

  const nav = [
    { label: "Overview", icon: LayoutDashboard, active: tab === "overview", onClick: () => setTab("overview") },
    { label: "Chargers", icon: Plug, active: tab === "chargers", onClick: () => setTab("chargers") },
    { label: "Earnings", icon: Banknote, active: tab === "earnings", onClick: () => setTab("earnings") },
  ];

  const withdraw = async () => {
    const v = Number(amount);
    if (!v || v <= 0) { toast.error("Enter amount"); return; }
    try {
      await api.post("/owner/withdraw", { amount: v });
      toast.success("Withdrawal requested"); setAmount(""); setWdOpen(false);
      qc.invalidateQueries();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const chartData = chargers.map((c) => ({ name: c.charger_id.replace("IND", "#"), kWh: c.energy_today }));

  return (
    <DashboardShell nav={nav} title="Owner Console">
      {tab === "overview" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6" data-testid="owner-overview">
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            <KPI icon={IndianRupee} label="Today's earnings" value={inr0(summary.today_earnings)} accent="text-charging" />
            <KPI icon={TrendingUp} label="This month" value={inr0(summary.month_earnings)} accent="text-charging" />
            <KPI icon={Zap} label="Units sold" value={`${summary.units_sold ?? 0}`} />
            <KPI icon={Wallet} label="Wallet" value={inr0(summary.wallet)} accent="text-wallet" />
          </div>
          <Card className="rounded-xl">
            <CardHeader><CardTitle className="font-display text-base">Energy delivered today (kWh)</CardTitle></CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="name" fontSize={11} /><YAxis fontSize={11} /><Tooltip contentStyle={{ borderRadius: 10, background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))" }} /><Bar dataKey="kWh" fill="hsl(var(--charging))" radius={[5, 5, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KPI icon={Plug} label="Total chargers" value={summary.chargers_total ?? 0} />
            <KPI icon={Zap} label="Online" value={summary.chargers_online ?? 0} accent="text-charging" />
            <KPI icon={LayoutDashboard} label="Sessions" value={summary.total_sessions ?? 0} />
          </div>
        </motion.div>
      )}

      {tab === "chargers" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="owner-chargers">
          {chargers.map((c) => (
            <div key={c.charger_id} className="rounded-xl border border-border/60 p-5">
              <div className="flex items-start justify-between">
                <div><p className="font-mono text-xs text-muted-foreground">{c.charger_id}</p><h3 className="font-medium mt-0.5">{c.name}</h3></div>
                <Badge className={`rounded-full ${statusBadge[c.status]}`}>{c.status}</Badge>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
                <span className="text-muted-foreground">Power</span><span className="font-mono text-right">{c.power_kw} kW</span>
                <span className="text-muted-foreground">Today</span><span className="font-mono text-right">{c.energy_today} kWh</span>
                <span className="text-muted-foreground">Price</span><span className="font-mono text-right">{inr(c.price_per_kwh)}</span>
                <span className="text-muted-foreground">Signal</span><span className="font-mono text-right">{c.online ? `${c.signal}/5` : "—"}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "earnings" && (
        <div className="space-y-6" data-testid="owner-earnings">
          <div className="rounded-xl border border-border/60 p-6 flex flex-wrap items-center justify-between gap-4">
            <div><p className="text-xs uppercase tracking-widest text-muted-foreground">Withdrawable balance</p><p className="font-mono text-4xl font-light tabular mt-1">{inr0(summary.wallet)}</p></div>
            <Dialog open={wdOpen} onOpenChange={setWdOpen}>
              <DialogTrigger asChild><Button data-testid="withdraw-btn" className="rounded-lg"><Banknote className="h-4 w-4 mr-2" /> Request withdrawal</Button></DialogTrigger>
              <DialogContent data-testid="withdraw-dialog">
                <DialogHeader><DialogTitle className="font-display">Request withdrawal</DialogTitle></DialogHeader>
                <p className="text-sm text-muted-foreground">Available: {inr(summary.wallet)}. Company verifies and transfers to your bank.</p>
                <Input data-testid="withdraw-amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Amount" className="h-12 font-mono" />
                <DialogFooter><Button onClick={withdraw} data-testid="withdraw-submit" className="rounded-lg">Submit request</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {withdrawals.length > 0 && (
            <Card className="rounded-xl"><CardHeader><CardTitle className="font-display text-base">Withdrawal requests</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {withdrawals.map((w) => (
                  <div key={w.id} className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                    <span className="font-mono">{inr(w.amount)}</span>
                    <div className="flex items-center gap-3"><span className="text-xs text-muted-foreground">{new Date(w.created_at).toLocaleDateString("en-IN")}</span><Badge variant="secondary" className="capitalize">{w.status}</Badge></div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          <Card className="rounded-xl"><CardHeader><CardTitle className="font-display text-base">Transactions</CardTitle></CardHeader>
            <CardContent>
              {txns.length === 0 ? <p className="text-sm text-muted-foreground">No earnings yet.</p> : (
                <div className="space-y-2" data-testid="owner-transactions">
                  {txns.map((t) => {
                    const credit = t.amount >= 0;
                    return (
                      <div key={t.id} className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                        <div className="flex items-center gap-3">
                          <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${credit ? "bg-charging/15" : "bg-secondary"}`}>{credit ? <ArrowDownLeft className="h-4 w-4 text-charging" /> : <ArrowUpRight className="h-4 w-4 text-muted-foreground" />}</div>
                          <div><p className="text-sm">{t.note}</p><p className="text-xs text-muted-foreground">{new Date(t.created_at).toLocaleString("en-IN")}</p></div>
                        </div>
                        <span className={`font-mono ${credit ? "text-charging" : ""}`}>{credit ? "+" : ""}{inr(t.amount)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}
