import { useQuery } from "@tanstack/react-query";
import { Zap, MapPin, ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, inr, fmtTime } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";

export default function HistoryPage() {
  const navigate = useNavigate();
  const { data: sessions = [] } = useQuery({ queryKey: ["sessions"], queryFn: async () => (await api.get("/sessions")).data });

  return (
    <CustomerShell>
      <div className="p-4 lg:p-8 max-w-3xl mx-auto lg:mx-0">
        <h1 className="font-display text-2xl font-semibold tracking-tight mb-5">Charging history</h1>
        {sessions.length === 0 ? <p className="text-sm text-muted-foreground">No charging sessions yet.</p> : (
          <div className="space-y-2" data-testid="history-list">
            {sessions.map((s) => {
              const active = s.status === "active";
              return (
                <button key={s.session_id} onClick={() => active && navigate(`/app/live/${s.session_id}`)} data-testid={`history-${s.session_id}`}
                  className="w-full text-left rounded-xl border border-border/60 p-4 flex items-center justify-between hover:bg-secondary/40 transition-colors duration-200">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-secondary flex items-center justify-center"><Zap className={`h-5 w-5 ${active ? "text-charging" : "text-muted-foreground"}`} /></div>
                    <div>
                      <p className="text-sm font-medium">{s.charger_name}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1"><MapPin className="h-3 w-3" /> {new Date(s.start_time).toLocaleString("en-IN")}</p>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-2">
                    {active ? <span className="text-xs font-semibold text-charging">Active</span> : (
                      <div><p className="font-mono font-medium">{inr(s.cost)}</p><p className="text-xs text-muted-foreground font-mono">{s.energy_kwh} kWh</p></div>
                    )}
                    {active && <ChevronRight className="h-4 w-4 text-charging" />}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </CustomerShell>
  );
}
