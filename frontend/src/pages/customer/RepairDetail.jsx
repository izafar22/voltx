import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Wrench, MapPin, Info, ShieldCheck, FileText, Calendar, Check, X, XCircle } from "lucide-react";
import { api, inr } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const STATUS_LABEL = {
  REQUESTED: "Requested", AWAITING_SHIPMENT: "Awaiting shipment", IN_TRANSIT_TO_VOLTX: "In transit to Voltx",
  RECEIVED_AT_VOLTX: "Received at Voltx", DIAGNOSING: "Diagnosing", ESTIMATE_SENT: "Estimate sent",
  CUSTOMER_APPROVED: "Approved", CUSTOMER_DECLINED: "Declined", REPAIRING: "Repairing",
  REPAIR_COMPLETED: "Repair completed", PAYMENT_PENDING: "Payment pending", READY_TO_SHIP: "Ready to ship",
  SHIPPED_TO_CUSTOMER: "Shipped", DELIVERED: "Delivered", COMPLETED: "Completed",
  CANCELLED: "Cancelled", NOT_REPAIRABLE: "Not repairable",
};

const ESTIMATE_STATUS_LABEL = { DRAFT: "Draft", SENT: "Sent", APPROVED: "Approved", DECLINED: "Declined" };
const ESTIMATE_BADGE = {
  DRAFT: "bg-secondary text-foreground", SENT: "bg-secondary text-foreground",
  APPROVED: "bg-charging/15 text-charging", DECLINED: "bg-destructive/15 text-destructive",
};
// Statuses from which the backend state machine does not allow CANCELLED
const NON_CANCELLABLE = ["SHIPPED_TO_CUSTOMER", "DELIVERED", "COMPLETED", "CANCELLED"];

const EstRow = ({ label, value }) => (
  <div className="flex items-center justify-between">
    <span className="text-muted-foreground">{label}</span>
    <span className="font-mono">{inr(value)}</span>
  </div>
);

export default function RepairDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(null); // target status while the PATCH request is in flight
  const [pendingAction, setPendingAction] = useState(null); // CUSTOMER_APPROVED | CUSTOMER_DECLINED | CANCELLED
  const { data: r, isLoading, isError, error } = useQuery({
    queryKey: ["repair", id],
    queryFn: async () => (await api.get(`/repairs/${id}`)).data,
    retry: false,
  });

  // Mirrors the backend exactly: approve/decline only from ESTIMATE_SENT and only with an estimate;
  // CANCELLED is reachable from every status except the post-shipment/terminal ones.
  const canDecide = !!r && r.status === "ESTIMATE_SENT" && !!r.estimate;
  const canCancel = !!r && !NON_CANCELLABLE.includes(r.status);

  const applyStatus = async (target) => {
    setBusy(target);
    try {
      await api.patch(`/repairs/${id}/status`, { status: target });
      toast.success(`Repair request ${STATUS_LABEL[target]?.toLowerCase() || "updated"}`);
      qc.invalidateQueries({ queryKey: ["repair", id] });
      qc.invalidateQueries({ queryKey: ["repairs-mine"] });
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not update repair request");
    } finally {
      setBusy(null);
      setPendingAction(null);
    }
  };

  return (
    <CustomerShell>
      <div className="p-4 lg:p-8 max-w-2xl mx-auto" data-testid="repair-detail-page">
        <button onClick={() => navigate("/app")} data-testid="detail-back-btn" className="flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 mb-4"><ArrowLeft className="h-4 w-4 mr-1" /> Back</button>

        {isLoading && <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-charging" /></div>}
        {isError && (
          <div className="rounded-xl border border-border/60 p-6 text-center" data-testid="repair-error">
            <p className="font-medium">{error?.response?.status === 403 ? "You don't have access to this repair request." : "Repair request not found."}</p>
            <Button variant="outline" className="mt-4 rounded-lg" onClick={() => navigate("/app")}>Back to Dashboard</Button>
          </div>
        )}

        {r && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 rounded-xl bg-charging/10 flex items-center justify-center"><Wrench className="h-6 w-6 text-charging" /></div>
                <div>
                  <p className="font-mono text-lg font-semibold" data-testid="detail-number">{r.repair_request_number}</p>
                  <p className="text-xs text-muted-foreground flex items-center gap-1"><Calendar className="h-3 w-3" /> {new Date(r.created_at).toLocaleString("en-IN")}</p>
                </div>
              </div>
              <Badge className="rounded-full bg-secondary text-foreground" data-testid="detail-status">{STATUS_LABEL[r.status] || r.status}</Badge>
            </div>

            <div className="mt-6 rounded-xl border border-border/60 p-4">
              <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Charger</p>
              <div className="grid grid-cols-2 gap-y-2 text-sm">
                {r.charger_id && <><span className="text-muted-foreground">Registered</span><span className="text-right font-mono">{r.charger_id}</span></>}
                <span className="text-muted-foreground">Brand</span><span className="text-right">{r.charger_info?.brand || "—"}</span>
                <span className="text-muted-foreground">Model</span><span className="text-right">{r.charger_info?.model || "—"}</span>
                <span className="text-muted-foreground">Type</span><span className="text-right">{r.charger_info?.charger_type || "—"}</span>
                {r.charger_info?.serial_number && <><span className="text-muted-foreground">Serial</span><span className="text-right">{r.charger_info.serial_number}</span></>}
                {r.charger_info?.power_rating && <><span className="text-muted-foreground">Power</span><span className="text-right">{r.charger_info.power_rating}</span></>}
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-border/60 p-4">
              <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Problem</p>
              {r.reported_category && <p className="font-medium">{r.reported_category}</p>}
              <p className="text-sm text-muted-foreground mt-1">{r.problem_description}</p>
            </div>

            {r.photos?.length > 0 && (
              <div className="mt-4 rounded-xl border border-border/60 p-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Photos ({r.photos.length})</p>
                <div className="flex flex-wrap gap-2" data-testid="detail-photos">
                  {r.photos.map((src, i) => <img key={i} src={src} alt={`photo ${i + 1}`} className="h-20 w-20 rounded-lg object-cover border border-border/60" />)}
                </div>
              </div>
            )}

            {r.estimate && (
              <div className="mt-4 rounded-xl border border-border/60 p-4" data-testid="estimate-section">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs uppercase tracking-widest text-muted-foreground">Repair estimate</p>
                  <Badge className={`rounded-full ${ESTIMATE_BADGE[r.estimate.status] || "bg-secondary text-foreground"}`} data-testid="estimate-status">
                    {ESTIMATE_STATUS_LABEL[r.estimate.status] || r.estimate.status}
                  </Badge>
                </div>
                <div className="space-y-1.5 text-sm">
                  {(r.estimate.parts || []).map((p, i) => (
                    <div key={i} className="flex items-center justify-between" data-testid={`estimate-part-${i}`}>
                      <span className="text-muted-foreground">{p.name}{p.qty > 1 ? ` × ${p.qty}` : ""}</span>
                      <span className="font-mono">{inr((p.price || 0) * (p.qty || 1))}</span>
                    </div>
                  ))}
                  {r.estimate.labor > 0 && <EstRow label="Labor" value={r.estimate.labor} />}
                  {r.estimate.diagnostic_fee > 0 && <EstRow label="Diagnostic fee" value={r.estimate.diagnostic_fee} />}
                  {r.estimate.incoming_logistics_cost > 0 && <EstRow label="Incoming logistics" value={r.estimate.incoming_logistics_cost} />}
                  {r.estimate.return_shipping_cost > 0 && <EstRow label="Return shipping" value={r.estimate.return_shipping_cost} />}
                  {r.estimate.other_charges > 0 && <EstRow label="Other charges" value={r.estimate.other_charges} />}
                  <div className="flex items-center justify-between border-t border-border/60 pt-2">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span className="font-mono">{inr(r.estimate.subtotal)}</span>
                  </div>
                  {r.estimate.tax > 0 && <EstRow label="Tax" value={r.estimate.tax} />}
                  <div className="flex items-center justify-between border-t border-border/60 pt-2 mt-1">
                    <span className="font-medium">Total</span>
                    <span className="font-mono font-semibold" data-testid="estimate-total">{inr(r.estimate.total)}</span>
                  </div>
                </div>
                {r.estimate.notes && <p className="text-sm text-muted-foreground mt-3">{r.estimate.notes}</p>}
                {r.estimate.status === "APPROVED" && r.estimate.approved_at && (
                  <p className="text-xs text-muted-foreground mt-3">Approved on {new Date(r.estimate.approved_at).toLocaleString("en-IN")}</p>
                )}
                {r.estimate.status === "DECLINED" && r.estimate.declined_at && (
                  <p className="text-xs text-muted-foreground mt-3">Declined on {new Date(r.estimate.declined_at).toLocaleString("en-IN")}</p>
                )}
              </div>
            )}

            <div className="mt-4 rounded-xl bg-secondary/50 border border-border/60 p-4 space-y-3 text-sm">
              <div className="flex gap-3"><MapPin className="h-5 w-5 text-charging shrink-0" /><div><p className="font-medium">Next step</p><p className="text-muted-foreground mt-0.5">Please send your charger to the Voltx service center. Shipping instructions will be provided by the Voltx service team.</p></div></div>
              <div className="flex gap-3"><Info className="h-5 w-5 text-muted-foreground shrink-0" /><p className="text-muted-foreground">Include your repair request number <span className="font-mono text-foreground">{r.repair_request_number}</span> with the charger.</p></div>
              <div className="flex gap-3"><ShieldCheck className="h-5 w-5 text-charging shrink-0" /><p className="text-muted-foreground">Payment is not required at this stage.</p></div>
            </div>

            {(canDecide || canCancel) && (
              <div className="mt-6 space-y-3">
                {canDecide && (
                  <div className="grid grid-cols-2 gap-3">
                    <Button onClick={() => setPendingAction("CUSTOMER_APPROVED")} disabled={!!busy} data-testid="estimate-approve-btn"
                      className="h-12 rounded-lg bg-charging text-black hover:bg-charging/90 active:scale-95 transition-transform duration-200">
                      <Check className="h-4 w-4 mr-1" /> Approve estimate
                    </Button>
                    <Button onClick={() => setPendingAction("CUSTOMER_DECLINED")} disabled={!!busy} variant="outline" data-testid="estimate-decline-btn"
                      className="h-12 rounded-lg border-destructive/40 text-destructive hover:bg-destructive/5 active:scale-95 transition-transform duration-200">
                      <X className="h-4 w-4 mr-1" /> Decline estimate
                    </Button>
                  </div>
                )}
                {canCancel && (
                  <Button onClick={() => setPendingAction("CANCELLED")} disabled={!!busy} variant="outline" data-testid="repair-cancel-btn"
                    className="w-full h-11 rounded-lg text-muted-foreground hover:text-destructive active:scale-95 transition-transform duration-200">
                    <XCircle className="h-4 w-4 mr-1" /> Cancel repair request
                  </Button>
                )}
              </div>
            )}

            <AlertDialog open={!!pendingAction} onOpenChange={(o) => { if (!o) setPendingAction(null); }}>
              <AlertDialogContent data-testid="repair-action-dialog">
                {pendingAction === "CUSTOMER_APPROVED" && (
                  <>
                    <AlertDialogHeader>
                      <AlertDialogTitle className="font-display">Approve repair estimate?</AlertDialogTitle>
                      <AlertDialogDescription>
                        You approve the repair work for {inr(r?.estimate?.total || 0)}. The Voltx repair team will proceed with the repair.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel data-testid="repair-action-dismiss">Not now</AlertDialogCancel>
                      <AlertDialogAction onClick={() => applyStatus("CUSTOMER_APPROVED")} disabled={!!busy} data-testid="repair-action-confirm"
                        className="bg-charging text-black hover:bg-charging/90">
                        {busy === "CUSTOMER_APPROVED" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Approve"}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </>
                )}
                {pendingAction === "CUSTOMER_DECLINED" && (
                  <>
                    <AlertDialogHeader>
                      <AlertDialogTitle className="font-display">Decline repair estimate?</AlertDialogTitle>
                      <AlertDialogDescription>
                        The repair will not be carried out and the Voltx team will arrange to return your charger.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel data-testid="repair-action-dismiss">Keep estimate</AlertDialogCancel>
                      <AlertDialogAction onClick={() => applyStatus("CUSTOMER_DECLINED")} disabled={!!busy} data-testid="repair-action-confirm"
                        className="bg-destructive text-white hover:bg-destructive/90">
                        {busy === "CUSTOMER_DECLINED" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Decline"}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </>
                )}
                {pendingAction === "CANCELLED" && (
                  <>
                    <AlertDialogHeader>
                      <AlertDialogTitle className="font-display">Cancel this repair request?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This cannot be undone. Request {r?.repair_request_number} will be closed.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel data-testid="repair-action-dismiss">Keep request</AlertDialogCancel>
                      <AlertDialogAction onClick={() => applyStatus("CANCELLED")} disabled={!!busy} data-testid="repair-action-confirm"
                        className="bg-destructive text-white hover:bg-destructive/90">
                        {busy === "CANCELLED" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Cancel request"}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </>
                )}
              </AlertDialogContent>
            </AlertDialog>
          </motion.div>
        )}
      </div>
    </CustomerShell>
  );
}
