import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { QrCode, Plus, Zap, ArrowRight, MapPin, Navigation, Wrench } from "lucide-react";
import { api, inr0 } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { StationsMap } from "@/components/StationsMap";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const dot = { Available: "bg-charging", Charging: "bg-amber-500", Offline: "bg-muted-foreground", Fault: "bg-destructive" };

export default function CustomerHome() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [code, setCode] = useState("");
  const [scanOpen, setScanOpen] = useState(false);

  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: async () => (await api.get("/wallet")).data });
  const { data: sessions = [] } = useQuery({ queryKey: ["sessions"], queryFn: async () => (await api.get("/sessions")).data });
  const { data: stations = [] } = useQuery({ queryKey: ["stations"], queryFn: async () => (await api.get("/stations")).data });
  const active = sessions.find((s) => s.status === "active");
  const available = stations.filter((s) => s.status === "Available").length;
  const charging = stations.filter((s) => s.status === "Charging").length;

  const goCharger = async (val) => {
    const cid = (val || code).trim().toUpperCase();
    if (!cid) return;
    try { await api.get(`/chargers/${cid}`); navigate(`/app/charger/${cid}`); }
    catch { toast.error("Charger not found. Try IND000001"); }
  };

  return (
    <CustomerShell>
      <div className="p-4 lg:p-8 space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm text-muted-foreground">Welcome back</p>
            <h1 className="font-display text-2xl lg:text-3xl font-semibold tracking-tight">{user?.name}</h1>
          </div>
          <Badge variant="secondary" className="rounded-full"><span className="h-2 w-2 rounded-full bg-charging mr-2" /> {available} stations available now</Badge>
        </div>

        {active && (
          <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => navigate(`/app/live/${active.session_id}`)} data-testid="active-session-banner"
            className="w-full rounded-2xl border border-charging/40 bg-charging/5 p-4 flex items-center justify-between text-left">
            <div className="flex items-center gap-3">
              <span className="relative flex h-3 w-3"><span className="animate-ping absolute h-3 w-3 rounded-full bg-charging opacity-75" /><span className="relative rounded-full h-3 w-3 bg-charging" /></span>
              <div><p className="font-semibold text-sm">Charging in progress</p><p className="text-xs text-muted-foreground">{active.charger_name}</p></div>
            </div>
            <ArrowRight className="h-5 w-5 text-charging" />
          </motion.button>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left column: wallet + actions */}
          <div className="space-y-4 lg:order-1 order-2">
            <div className="rounded-2xl bg-primary text-primary-foreground p-6 relative overflow-hidden" data-testid="wallet-card">
              <div className="absolute inset-0 grain opacity-30" />
              <div className="relative">
                <p className="text-xs uppercase tracking-[0.2em] text-primary-foreground/60">Wallet balance</p>
                <p className="font-mono text-4xl font-light tabular mt-1">{inr0(wallet?.balance)}</p>
                <Button onClick={() => navigate("/app/wallet")} data-testid="add-money-btn" size="sm" className="mt-5 rounded-full bg-charging text-black hover:bg-charging/90 active:scale-95 transition-transform duration-200"><Plus className="h-4 w-4 mr-1" /> Add money</Button>
              </div>
            </div>

            <Dialog open={scanOpen} onOpenChange={setScanOpen}>
              <DialogTrigger asChild>
                <button data-testid="scan-qr-btn" className="w-full rounded-2xl border border-border/60 p-5 flex items-center gap-4 hover:bg-secondary/50 transition-colors duration-200 active:scale-[0.98]">
                  <div className="h-11 w-11 rounded-xl bg-charging/10 flex items-center justify-center"><QrCode className="h-6 w-6 text-charging" strokeWidth={1.5} /></div>
                  <div className="text-left"><p className="font-semibold">Scan QR</p><p className="text-xs text-muted-foreground">Scan a charger to start</p></div>
                </button>
              </DialogTrigger>
              <DialogContent data-testid="scan-dialog">
                <DialogHeader><DialogTitle className="font-display">Scan charger QR</DialogTitle></DialogHeader>
                <div className="aspect-square rounded-xl border-2 border-dashed border-border flex flex-col items-center justify-center gap-3 text-muted-foreground">
                  <QrCode className="h-16 w-16" strokeWidth={1} /><p className="text-sm text-center px-6">Camera scanning is simulated in demo.<br />Enter a station ID below.</p>
                </div>
                <div className="flex gap-2"><Input data-testid="scan-code-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. IND000001" className="h-12 font-mono" /><Button onClick={() => { setScanOpen(false); goCharger(); }} data-testid="scan-go-btn" className="h-12 rounded-lg">Go</Button></div>
              </DialogContent>
            </Dialog>

            <button data-testid="repair-charger-btn" onClick={() => navigate("/repairs/new")} className="w-full rounded-2xl border border-border/60 p-5 flex items-center gap-4 hover:bg-secondary/50 transition-colors duration-200 active:scale-[0.98]">
              <div className="h-11 w-11 rounded-xl bg-wallet/10 flex items-center justify-center"><Wrench className="h-6 w-6 text-wallet" strokeWidth={1.5} /></div>
              <div className="text-left"><p className="font-semibold">Repair a Charger</p><p className="text-xs text-muted-foreground">Any brand · AC, DC or portable</p></div>
            </button>

            <div className="rounded-2xl border border-border/60 p-5">
              <div className="flex items-center gap-2 mb-3"><Zap className="h-5 w-5 text-charging" strokeWidth={1.5} /><p className="font-semibold">Enter station code</p></div>
              <div className="flex gap-2">
                <Input data-testid="station-code-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="IND000001" className="h-11 font-mono" onKeyDown={(e) => e.key === "Enter" && goCharger()} />
                <Button onClick={() => goCharger()} data-testid="code-go-btn" size="icon" className="h-11 w-11 shrink-0 rounded-lg"><ArrowRight className="h-4 w-4" /></Button>
              </div>
            </div>

            <div className="rounded-2xl border border-border/60 p-5">
              <p className="text-xs uppercase tracking-widest text-muted-foreground mb-3">Network status</p>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div><p className="font-mono text-2xl font-light text-charging">{available}</p><p className="text-xs text-muted-foreground">Available</p></div>
                <div><p className="font-mono text-2xl font-light text-amber-500">{charging}</p><p className="text-xs text-muted-foreground">In use</p></div>
                <div><p className="font-mono text-2xl font-light">{stations.length}</p><p className="text-xs text-muted-foreground">Total</p></div>
              </div>
            </div>
          </div>

          {/* Center/right: map */}
          <div className="lg:col-span-2 lg:order-2 order-1 rounded-2xl border border-border/60 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b border-border/60">
              <div className="flex items-center gap-2"><Navigation className="h-4.5 w-4.5 text-charging" strokeWidth={1.5} /><h2 className="font-display font-semibold">Nearby charging stations</h2></div>
              <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
                {["Available", "Charging", "Offline", "Fault"].map((s) => <span key={s} className="flex items-center gap-1"><span className={`h-2 w-2 rounded-full ${dot[s]}`} />{s}</span>)}
              </div>
            </div>
            <div className="h-[380px] lg:h-[560px]"><StationsMap stations={stations} /></div>
          </div>
        </div>

        {/* Recent charging */}
        <div>
          <h2 className="font-display text-lg font-semibold mb-3">Recent charging</h2>
          {sessions.length === 0 ? <p className="text-sm text-muted-foreground">No sessions yet. Pick a station on the map to begin.</p> : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="recent-sessions">
              {sessions.slice(0, 6).map((s) => (
                <div key={s.session_id} className="rounded-xl border border-border/60 p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-secondary flex items-center justify-center"><Zap className={`h-4.5 w-4.5 ${s.status === "active" ? "text-charging" : "text-muted-foreground"}`} /></div>
                    <div><p className="text-sm font-medium">{s.charger_name}</p><p className="text-xs text-muted-foreground flex items-center gap-1"><MapPin className="h-3 w-3" /> {new Date(s.start_time).toLocaleDateString("en-IN")}</p></div>
                  </div>
                  <div className="text-right">
                    {s.status === "active" ? <span className="text-xs font-semibold text-charging">Active</span> : <><p className="font-mono text-sm">{inr0(s.cost)}</p><p className="text-xs text-muted-foreground font-mono">{s.energy_kwh} kWh</p></>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </CustomerShell>
  );
}
