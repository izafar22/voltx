import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useState } from "react";
import { ArrowLeft, Zap, MapPin, User, Plug, IndianRupee, Loader2 } from "lucide-react";
import { api, inr } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const stateStyle = {
  Available: "bg-charging/15 text-charging border-charging/30",
  Charging: "bg-amber-500/15 text-amber-500 border-amber-500/30",
  Offline: "bg-muted text-muted-foreground border-border",
  Fault: "bg-destructive/15 text-destructive border-destructive/30",
};

export default function ChargerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const { data: c, isLoading } = useQuery({ queryKey: ["charger", id], queryFn: async () => (await api.get(`/chargers/${id}`)).data });
  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: async () => (await api.get("/wallet")).data });

  const start = async () => {
    setStarting(true);
    try {
      const { data } = await api.post("/sessions/start", { charger_id: id });
      toast.success("Charging started");
      navigate(`/app/live/${data.session_id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start charging");
    } finally { setStarting(false); }
  };

  return (
    <CustomerShell>
      <div className="p-4 lg:p-8 max-w-lg mx-auto">
        <button onClick={() => navigate("/app")} data-testid="back-btn" className="flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 mb-5"><ArrowLeft className="h-4 w-4 mr-1" /> Back</button>
        {isLoading || !c ? <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-charging" /></div> : (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} data-testid="charger-detail">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-sm text-muted-foreground">{c.charger_id}</p>
                <h1 className="font-display text-2xl font-semibold tracking-tight mt-0.5">{c.name}</h1>
                <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1"><MapPin className="h-3.5 w-3.5" /> {c.location}</p>
              </div>
              <Badge className={`rounded-full border ${stateStyle[c.status] || stateStyle.Offline}`} data-testid="charger-status">{c.status}</Badge>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              {[
                { icon: IndianRupee, label: "Price", value: `${inr(c.price_per_kwh)}/kWh` },
                { icon: Zap, label: "Max power", value: `${c.max_power_kw} kW` },
                { icon: Plug, label: "Connector", value: c.connector },
                { icon: User, label: "Owner", value: c.owner_name },
              ].map((m) => (
                <div key={m.label} className="rounded-xl border border-border/60 p-4">
                  <m.icon className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
                  <p className="text-xs uppercase tracking-widest text-muted-foreground mt-2">{m.label}</p>
                  <p className="font-medium mt-0.5">{m.value}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-xl border border-border/60 p-4 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Your wallet</span>
              <span className="font-mono font-semibold">{inr(wallet?.balance)}</span>
            </div>

            <Button onClick={start} disabled={starting || c.status !== "Available"} data-testid="start-charging-btn"
              className="w-full h-14 mt-6 rounded-xl text-base bg-charging text-black hover:bg-charging/90 active:scale-95 transition-transform duration-200 disabled:opacity-50">
              {starting ? <Loader2 className="h-5 w-5 animate-spin" /> : c.status === "Available" ? <><Zap className="h-5 w-5 mr-2" fill="currentColor" /> Start charging</> : `Charger ${c.status}`}
            </Button>
          </motion.div>
        )}
      </div>
    </CustomerShell>
  );
}
