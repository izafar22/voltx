import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { QrCode, Plus, Zap, ArrowRight, MapPin } from "lucide-react";
import { api, inr0, fmtTime } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const stateColor = {
  Available: "text-charging", Charging: "text-charging", Preparing: "text-amber-500",
  Finishing: "text-amber-500", Offline: "text-muted-foreground", Fault: "text-destructive",
};

export default function CustomerHome() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [code, setCode] = useState("");
  const [scanOpen, setScanOpen] = useState(false);

  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: async () => (await api.get("/wallet")).data });
  const { data: sessions = [] } = useQuery({ queryKey: ["sessions"], queryFn: async () => (await api.get("/sessions")).data });
  const active = sessions.find((s) => s.status === "active");

  const goCharger = async () => {
    const cid = code.trim().toUpperCase();
    if (!cid) return;
    try {
      await api.get(`/chargers/${cid}`);
      navigate(`/app/charger/${cid}`);
    } catch { toast.error("Charger not found. Try IND000001"); }
  };

  return (
    <CustomerShell>
      <div className="p-5 space-y-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <p className="text-sm text-muted-foreground">Welcome back</p>
          <h1 className="font-display text-2xl font-semibold tracking-tight">{user?.name}</h1>
        </motion.div>

        {/* Wallet card */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="rounded-2xl bg-primary text-primary-foreground p-6 relative overflow-hidden" data-testid="wallet-card">
          <div className="absolute inset-0 grain opacity-30" />
          <div className="relative">
            <p className="text-xs uppercase tracking-[0.2em] text-primary-foreground/60">Wallet balance</p>
            <p className="font-mono text-4xl font-light tabular mt-1">{inr0(wallet?.balance)}</p>
            <div className="mt-5 flex gap-2">
              <Button onClick={() => navigate("/app/wallet")} data-testid="add-money-btn" size="sm" className="rounded-full bg-charging text-black hover:bg-charging/90 active:scale-95 transition-transform duration-200"><Plus className="h-4 w-4 mr-1" /> Add money</Button>
            </div>
          </div>
        </motion.div>

        {/* Active session banner */}
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

        {/* Scan / enter code */}
        <div className="grid grid-cols-2 gap-3">
          <Dialog open={scanOpen} onOpenChange={setScanOpen}>
            <DialogTrigger asChild>
              <button data-testid="scan-qr-btn" className="rounded-2xl border border-border/60 p-5 flex flex-col items-start gap-3 hover:bg-secondary/50 transition-colors duration-200 active:scale-95">
                <QrCode className="h-7 w-7 text-charging" strokeWidth={1.5} />
                <span className="font-semibold">Scan QR</span>
              </button>
            </DialogTrigger>
            <DialogContent data-testid="scan-dialog">
              <DialogHeader><DialogTitle className="font-display">Scan charger QR</DialogTitle></DialogHeader>
              <div className="aspect-square rounded-xl border-2 border-dashed border-border flex flex-col items-center justify-center gap-3 text-muted-foreground">
                <QrCode className="h-16 w-16" strokeWidth={1} />
                <p className="text-sm text-center px-6">Camera scanning is simulated in demo.<br />Enter a station ID below.</p>
              </div>
              <div className="flex gap-2">
                <Input data-testid="scan-code-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. IND000001" className="h-12 font-mono" />
                <Button onClick={() => { setScanOpen(false); goCharger(); }} data-testid="scan-go-btn" className="h-12 rounded-lg">Go</Button>
              </div>
            </DialogContent>
          </Dialog>

          <div className="rounded-2xl border border-border/60 p-5 flex flex-col gap-3">
            <Zap className="h-7 w-7 text-charging" strokeWidth={1.5} />
            <span className="font-semibold">Enter code</span>
            <div className="flex gap-2 mt-auto">
              <Input data-testid="station-code-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="IND000001" className="h-10 font-mono text-sm" onKeyDown={(e) => e.key === "Enter" && goCharger()} />
              <Button onClick={goCharger} data-testid="code-go-btn" size="icon" className="h-10 w-10 shrink-0 rounded-lg"><ArrowRight className="h-4 w-4" /></Button>
            </div>
          </div>
        </div>

        {/* Recent sessions */}
        <div>
          <h2 className="font-display text-lg font-semibold mb-3">Recent charging</h2>
          {sessions.length === 0 ? <p className="text-sm text-muted-foreground">No sessions yet. Scan a charger to begin.</p> : (
            <div className="space-y-2" data-testid="recent-sessions">
              {sessions.slice(0, 4).map((s) => (
                <div key={s.session_id} className="rounded-xl border border-border/60 p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-secondary flex items-center justify-center"><Zap className={`h-4.5 w-4.5 ${s.status === "active" ? "text-charging" : "text-muted-foreground"}`} /></div>
                    <div><p className="text-sm font-medium">{s.charger_name}</p><p className="text-xs text-muted-foreground flex items-center gap-1"><MapPin className="h-3 w-3" /> {new Date(s.start_time).toLocaleDateString("en-IN")}</p></div>
                  </div>
                  <div className="text-right">
                    {s.status === "active" ? <span className={`text-xs font-semibold ${stateColor.Charging}`}>Active</span>
                      : <><p className="font-mono text-sm">{inr0(s.cost)}</p><p className="text-xs text-muted-foreground font-mono">{s.energy_kwh} kWh</p></>}
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
