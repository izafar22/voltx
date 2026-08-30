import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Loader2, Wrench, MapPin, Info, ShieldCheck, FileText, Calendar } from "lucide-react";
import { api } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const STATUS_LABEL = {
  REQUESTED: "Requested", AWAITING_SHIPMENT: "Awaiting shipment", IN_TRANSIT_TO_VOLTX: "In transit to Voltx",
  RECEIVED_AT_VOLTX: "Received at Voltx", DIAGNOSING: "Diagnosing", ESTIMATE_SENT: "Estimate sent",
  CUSTOMER_APPROVED: "Approved", CUSTOMER_DECLINED: "Declined", REPAIRING: "Repairing",
  REPAIR_COMPLETED: "Repair completed", PAYMENT_PENDING: "Payment pending", READY_TO_SHIP: "Ready to ship",
  SHIPPED_TO_CUSTOMER: "Shipped", DELIVERED: "Delivered", COMPLETED: "Completed",
  CANCELLED: "Cancelled", NOT_REPAIRABLE: "Not repairable",
};

export default function RepairDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: r, isLoading, isError, error } = useQuery({
    queryKey: ["repair", id],
    queryFn: async () => (await api.get(`/repairs/${id}`)).data,
    retry: false,
  });

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

            <div className="mt-4 rounded-xl bg-secondary/50 border border-border/60 p-4 space-y-3 text-sm">
              <div className="flex gap-3"><MapPin className="h-5 w-5 text-charging shrink-0" /><div><p className="font-medium">Next step</p><p className="text-muted-foreground mt-0.5">Please send your charger to the Voltx service center. Shipping instructions will be provided by the Voltx service team.</p></div></div>
              <div className="flex gap-3"><Info className="h-5 w-5 text-muted-foreground shrink-0" /><p className="text-muted-foreground">Include your repair request number <span className="font-mono text-foreground">{r.repair_request_number}</span> with the charger.</p></div>
              <div className="flex gap-3"><ShieldCheck className="h-5 w-5 text-charging shrink-0" /><p className="text-muted-foreground">Payment is not required at this stage.</p></div>
            </div>
          </motion.div>
        )}
      </div>
    </CustomerShell>
  );
}
