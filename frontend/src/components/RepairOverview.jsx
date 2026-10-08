import { useNavigate } from "react-router-dom";
import { ArrowRight, Wrench } from "lucide-react";
import { useMyRepairs } from "../hooks/useMyRepairs";
import { REPAIR_STATUS_LABEL } from "../lib/repairStatus";
import { Button } from "./ui/button";

export function RepairOverview() {
  const navigate = useNavigate();
  const { data: repairs = [], isPending, isError, refetch } = useMyRepairs();

  return <section aria-labelledby="repair-history-title">
    <div className="dashboard-repair-heading">
      <div><h2 id="repair-history-title" className="font-display text-lg font-semibold">My Repair Requests</h2><p className="text-sm text-muted-foreground mt-1">Your latest requests and their current status.</p></div>
      <Button variant="outline" className="min-h-11" onClick={() => navigate("/repairs")} data-testid="view-all-repairs">View all repairs<ArrowRight aria-hidden="true" className="h-4 w-4 ml-2" /></Button>
    </div>
    {isPending ? (
      <p role="status" className="dashboard-card p-5">Loading repair requests…</p>
    ) : isError ? (
      <div role="alert" className="dashboard-card p-5"><p>Unable to load repair requests.</p><Button variant="outline" className="mt-3 min-h-11" onClick={() => refetch()}>Retry</Button></div>
    ) : repairs.length === 0 ? (
      <div className="dashboard-card p-6"><Wrench aria-hidden="true" className="h-6 w-6 text-muted-foreground mb-3" /><p className="font-medium">No repair requests yet</p><p className="text-sm text-muted-foreground mt-2">Start with Repair a Charger. Your requests and status updates will appear here.</p></div>
    ) : (
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {repairs.slice(0, 6).map((repair) => (
          <button key={repair.id} onClick={() => navigate(`/repairs/${repair.id}`)} className="dashboard-card dashboard-repair-item" data-testid={`dashboard-repair-${repair.id}`}>
            <span><strong className="block font-mono text-sm">{repair.repair_request_number}</strong><span className="block text-sm mt-2">{repair.charger_info?.brand || repair.charger_id || "Charger"}{repair.charger_info?.model ? ` · ${repair.charger_info.model}` : ""}</span><span className="inline-block rounded-md bg-secondary px-2 py-1 text-xs mt-3">{REPAIR_STATUS_LABEL[repair.status] || repair.status}</span></span>
            <ArrowRight aria-hidden="true" className="h-4 w-4 shrink-0" />
          </button>
        ))}
      </div>
    )}
  </section>;
}
