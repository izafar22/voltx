import { useNavigate } from "react-router-dom";
import { useMyRepairs } from "../../hooks/useMyRepairs";
import { motion } from "framer-motion";
import { Wrench, ChevronRight, Plus, Calendar } from "lucide-react";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Button } from "@/components/ui/button";
import { RepairStatus } from "../../components/patterns/RepairStatus";


export default function RepairsList() {
  const navigate = useNavigate();
  const { data: repairs = [], isLoading, isError, refetch } = useMyRepairs();

  return (
    <CustomerShell>
      <div className="p-4 lg:p-8 max-w-2xl mx-auto" data-testid="repairs-list-page">
        <div className="flex items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight">My Repairs</h1>
            <p className="text-sm text-muted-foreground">Track your EV charger repair requests.</p>
          </div>
          <Button onClick={() => navigate("/repairs/new")} data-testid="new-repair-btn" className="rounded-lg shrink-0"><Plus className="h-4 w-4 mr-1" /> New</Button>
        </div>

        {isLoading ? (
          <p className="text-sm text-muted-foreground py-10 text-center">Loading...</p>
        ) : isError ? (
          <div role="alert" className="rounded-xl border border-border/60 p-6"><p>Unable to load repair requests.</p><Button variant="outline" className="mt-3 min-h-11" onClick={() => refetch()}>Retry</Button></div>
        ) : repairs.length === 0 ? (
          <div className="rounded-xl border border-border/60 p-8 text-center" data-testid="repairs-empty">
            <div className="mx-auto h-12 w-12 rounded-xl bg-charging/10 flex items-center justify-center"><Wrench className="h-6 w-6 text-charging" /></div>
            <p className="mt-3 font-medium">No repair requests yet</p>
            <p className="text-sm text-muted-foreground mt-1">Get an EV charger of any brand diagnosed and repaired by RushX.</p>
            <Button onClick={() => navigate("/repairs/new")} data-testid="empty-new-repair-btn" className="mt-4 rounded-lg">Repair a Charger</Button>
          </div>
        ) : (
          <div className="space-y-2" data-testid="repairs-list">
            {repairs.map((r, i) => (
              <motion.button key={r.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                onClick={() => navigate(`/repairs/${r.id}`)} data-testid={`repair-item-${r.id}`}
                className="w-full text-left rounded-xl border border-border/60 p-4 flex items-center justify-between gap-3 hover:bg-secondary/40 transition-colors duration-200">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold">{r.repair_request_number}</span>
                    <RepairStatus status={r.status} />
                  </div>
                  <p className="text-sm text-muted-foreground truncate mt-0.5">
                    {(r.charger_info?.brand || r.charger_id || "Charger")}{r.charger_info?.model ? ` · ${r.charger_info.model}` : ""} — {r.problem_description}
                  </p>
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1"><Calendar className="h-3 w-3" /> {new Date(r.created_at).toLocaleDateString("en-IN")}</p>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0" />
              </motion.button>
            ))}
          </div>
        )}
      </div>
    </CustomerShell>
  );
}
