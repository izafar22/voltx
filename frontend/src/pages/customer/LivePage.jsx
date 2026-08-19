import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Zap, Clock, Gauge, IndianRupee, Loader2, Power } from "lucide-react";
import { api, inr, fmtTime } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { ChargingRing } from "@/components/ChargingRing";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function LivePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [stopping, setStopping] = useState(false);

  const { data } = useQuery({
    queryKey: ["live", id],
    queryFn: async () => (await api.get(`/sessions/${id}/live`)).data,
    refetchInterval: 2000,
  });

  const live = data?.live || {};
  const stopped = data && data.status !== "active";

  const stop = async () => {
    setStopping(true);
    try {
      const { data: res } = await api.post(`/sessions/${id}/stop`);
      toast.success("Charging stopped", { description: `${res.energy_kwh} kWh · ${inr(res.cost)} charged` });
      qc.invalidateQueries();
      navigate("/app/history");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not stop");
      setStopping(false);
    }
  };

  const metrics = [
    { icon: Zap, label: "Energy", value: `${live.energy_kwh ?? 0}`, unit: "kWh" },
    { icon: Clock, label: "Time", value: fmtTime(live.elapsed_seconds), unit: "" },
    { icon: Gauge, label: "Power", value: `${live.power_kw ?? 0}`, unit: "kW" },
    { icon: IndianRupee, label: "Est. cost", value: `${(live.cost ?? 0).toFixed(2)}`, unit: "₹" },
  ];

  return (
    <CustomerShell>
      <div className="p-5 flex flex-col items-center" data-testid="live-page">
        {!data ? <div className="py-24"><Loader2 className="h-6 w-6 animate-spin text-charging" /></div> : (
          <>
            <div className="text-center mb-2">
              <p className="text-xs uppercase tracking-[0.2em] text-charging flex items-center justify-center gap-1.5">
                <span className="relative flex h-2 w-2"><span className={`${!stopped ? "animate-ping" : ""} absolute h-2 w-2 rounded-full bg-charging opacity-75`} /><span className="relative rounded-full h-2 w-2 bg-charging" /></span>
                {stopped ? "Session ended" : "Charging live"}
              </p>
              <h1 className="font-display text-xl font-semibold mt-1">{data.charger_name}</h1>
            </div>

            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="my-6">
              <ChargingRing soc={live.soc ?? 0} active={!stopped} />
            </motion.div>

            <div className="grid grid-cols-2 gap-3 w-full">
              {metrics.map((m) => (
                <div key={m.label} className="rounded-xl border border-border/60 p-4">
                  <m.icon className="h-4.5 w-4.5 text-muted-foreground" strokeWidth={1.5} />
                  <p className="text-xs uppercase tracking-widest text-muted-foreground mt-2">{m.label}</p>
                  <p className="font-mono text-2xl font-light tabular mt-0.5" data-testid={`metric-${m.label.toLowerCase().replace(/[.\s]/g, "")}`}>
                    {m.unit === "₹" && "₹"}{m.value}{m.unit && m.unit !== "₹" && <span className="text-sm text-muted-foreground ml-1">{m.unit}</span>}
                  </p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3 w-full mt-3 text-center">
              <div className="rounded-xl bg-secondary/50 p-3"><p className="text-xs text-muted-foreground">Voltage</p><p className="font-mono font-medium">{live.voltage ?? 0} V</p></div>
              <div className="rounded-xl bg-secondary/50 p-3"><p className="text-xs text-muted-foreground">Current</p><p className="font-mono font-medium">{live.current ?? 0} A</p></div>
            </div>
          </>
        )}
      </div>

      {data && !stopped && (
        <div className="fixed bottom-16 left-1/2 -translate-x-1/2 w-full max-w-md p-5 glass border-t z-30">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button data-testid="stop-charging-btn" className="w-full h-14 rounded-xl text-base bg-destructive text-white hover:bg-destructive/90 active:scale-95 transition-transform duration-200">
                <Power className="h-5 w-5 mr-2" /> Stop charging
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent data-testid="stop-confirm-dialog">
              <AlertDialogHeader><AlertDialogTitle>Stop charging?</AlertDialogTitle><AlertDialogDescription>You'll be billed {inr(live.cost ?? 0)} for {live.energy_kwh ?? 0} kWh.</AlertDialogDescription></AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel data-testid="stop-cancel">Keep charging</AlertDialogCancel>
                <AlertDialogAction onClick={stop} disabled={stopping} data-testid="stop-confirm" className="bg-destructive hover:bg-destructive/90">{stopping ? <Loader2 className="h-4 w-4 animate-spin" /> : "Stop & pay"}</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      )}
    </CustomerShell>
  );
}
