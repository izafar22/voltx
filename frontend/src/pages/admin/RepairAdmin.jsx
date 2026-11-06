import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Plus, Trash2, XCircle, Info, Send, Wrench } from "lucide-react";
import { listRepairs } from "../../lib/repairApi";
import RepairPaymentPanel from "../../components/RepairPaymentPanel";
import RepairPaymentVerification from "../../components/RepairPaymentVerification";
import { api, inr, inr0 } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";

const REPAIR_STATUS_LABEL = {
  REQUESTED: "Requested", AWAITING_SHIPMENT: "Awaiting shipment", IN_TRANSIT_TO_VOLTX: "In transit",
  RECEIVED_AT_VOLTX: "Received", DIAGNOSING: "Diagnosing", ESTIMATE_SENT: "Estimate sent",
  CUSTOMER_APPROVED: "Customer approved", CUSTOMER_DECLINED: "Customer declined", REPAIRING: "Repairing",
  REPAIR_COMPLETED: "Repair completed", PAYMENT_PENDING: "Payment pending", READY_TO_SHIP: "Ready to ship",
  SHIPPED_TO_CUSTOMER: "Shipped", DELIVERED: "Delivered", COMPLETED: "Completed",
  CANCELLED: "Cancelled", NOT_REPAIRABLE: "Not repairable",
};

const REPAIR_STATUS_BADGE = {
  REQUESTED: "bg-secondary text-foreground", AWAITING_SHIPMENT: "bg-secondary text-foreground",
  IN_TRANSIT_TO_VOLTX: "bg-wallet/15 text-wallet", RECEIVED_AT_VOLTX: "bg-wallet/15 text-wallet",
  DIAGNOSING: "bg-amber-500/15 text-amber-500", ESTIMATE_SENT: "bg-amber-500/15 text-amber-500",
  CUSTOMER_APPROVED: "bg-charging/15 text-charging", CUSTOMER_DECLINED: "bg-destructive/15 text-destructive",
  REPAIRING: "bg-amber-500/15 text-amber-500", REPAIR_COMPLETED: "bg-amber-500/15 text-amber-500",
  PAYMENT_PENDING: "bg-amber-500/15 text-amber-500", READY_TO_SHIP: "bg-wallet/15 text-wallet",
  SHIPPED_TO_CUSTOMER: "bg-wallet/15 text-wallet", DELIVERED: "bg-charging/15 text-charging",
  COMPLETED: "bg-charging/15 text-charging", CANCELLED: "bg-muted text-muted-foreground",
  NOT_REPAIRABLE: "bg-destructive/15 text-destructive",
};

// UI affordance only — the backend REPAIR_TRANSITIONS map (server.py) remains the source of truth;
// any invalid offer surfaces as a 400 toast instead of being silently accepted.
const REPAIR_NEXT = {
  REQUESTED: ["AWAITING_SHIPMENT", "CANCELLED"],
  AWAITING_SHIPMENT: ["IN_TRANSIT_TO_VOLTX", "CANCELLED"],
  IN_TRANSIT_TO_VOLTX: ["RECEIVED_AT_VOLTX", "CANCELLED"],
  RECEIVED_AT_VOLTX: ["DIAGNOSING", "CANCELLED"],
  DIAGNOSING: ["ESTIMATE_SENT", "NOT_REPAIRABLE", "CANCELLED"],
  ESTIMATE_SENT: ["CUSTOMER_APPROVED", "CUSTOMER_DECLINED", "CANCELLED"],
  CUSTOMER_APPROVED: ["REPAIRING", "CANCELLED"],
  CUSTOMER_DECLINED: ["READY_TO_SHIP", "CANCELLED"],
  NOT_REPAIRABLE: ["READY_TO_SHIP", "CANCELLED"],
  REPAIRING: ["REPAIR_COMPLETED", "CANCELLED"],
  REPAIR_COMPLETED: ["PAYMENT_PENDING", "CANCELLED"],
  PAYMENT_PENDING: ["READY_TO_SHIP", "CANCELLED"],
  READY_TO_SHIP: ["SHIPPED_TO_CUSTOMER", "CANCELLED"],
  SHIPPED_TO_CUSTOMER: ["DELIVERED"],
  DELIVERED: ["COMPLETED"],
  COMPLETED: [],
  CANCELLED: [],
};

// Customer decisions are surfaced as status info; the admin console does not set them on the customer's behalf.
const CUSTOMER_DECISIONS = ["CUSTOMER_APPROVED", "CUSTOMER_DECLINED"];

export default function RepairAdmin() {
  const { data: repairs = [], isLoading, isError, refetch } = useQuery({ queryKey: ["repairs-all"], queryFn: () => listRepairs("all") });
  const { data: customers = [] } = useQuery({ queryKey: ["repair-admin-users"], queryFn: async () => (await api.get("/admin/users")).data });
  // Registered charger lookup is a parked network feature; repair records carry charger_info.
  return <CustomerShell><main className="p-4 lg:p-8 max-w-6xl mx-auto space-y-5">
    <h1 className="font-display text-2xl font-semibold">Repair administration</h1>
    {isLoading ? <p>Loading repairs…</p> : isError ? <div role="alert">Could not load repairs. <Button onClick={() => refetch()}>Retry</Button></div> : <RepairsTab repairs={repairs} customers={customers} chargers={[]} />}
  </main></CustomerShell>;
}

// ==================== Admin Repair Console ====================

function RepairsTab({ repairs, customers, chargers }) {
  const [selectedId, setSelectedId] = useState(null);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const custById = Object.fromEntries(customers.map((u) => [u.user_id, u]));
  const chargerById = Object.fromEntries(chargers.map((c) => [c.charger_id, c]));

  const filtered = repairs.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    const needle = q.trim().toLowerCase();
    if (!needle) return true;
    const cust = custById[r.user_id];
    return [
      r.repair_request_number, r.status, r.charger_id,
      r.charger_info?.brand, r.charger_info?.model, r.charger_info?.serial_number,
      r.reported_category, r.problem_description, cust?.name, cust?.phone,
    ].filter(Boolean).join(" ").toLowerCase().includes(needle);
  });

  if (selectedId) {
    return <RepairDetailPanel key={selectedId} id={selectedId} onBack={() => setSelectedId(null)} custById={custById} chargerById={chargerById} />;
  }

  return (
    <div className="space-y-4" data-testid="admin-repairs">
      <div className="flex flex-wrap items-center gap-3">
        <Input data-testid="repairs-search" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Search REP no., status, charger, customer, problem…" className="h-11 max-w-sm" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger data-testid="repairs-status-filter" className="h-11 w-52"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {Object.keys(REPAIR_STATUS_LABEL).map((s) => <SelectItem key={s} value={s}>{REPAIR_STATUS_LABEL[s]}</SelectItem>)}
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground ml-auto" data-testid="repairs-count">{filtered.length} of {repairs.length} requests</p>
      </div>

      <Card className="rounded-xl">
        <CardContent className="p-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow><TableHead>Request</TableHead><TableHead>Status</TableHead><TableHead>Charger</TableHead><TableHead>Customer</TableHead><TableHead>Created</TableHead><TableHead className="text-right">Estimate</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">No repair requests match.</TableCell></TableRow>
              ) : filtered.map((r) => (
                <TableRow key={r.id} onClick={() => setSelectedId(r.id)} data-testid={`repair-row-${r.id}`}
                  className="cursor-pointer hover:bg-secondary/40 transition-colors duration-150">
                  <TableCell className="font-mono font-medium">{r.repair_request_number}</TableCell>
                  <TableCell><Badge className={`rounded-full ${REPAIR_STATUS_BADGE[r.status] || "bg-secondary text-foreground"}`}>{REPAIR_STATUS_LABEL[r.status] || r.status}</Badge></TableCell>
                  <TableCell className="text-sm">{r.charger_id || [r.charger_info?.brand, r.charger_info?.model].filter(Boolean).join(" ") || "—"}</TableCell>
                  <TableCell className="text-sm">{custById[r.user_id]?.name || <span className="font-mono text-xs">{r.user_id}</span>}</TableCell>
                  <TableCell className="text-sm">{new Date(r.created_at).toLocaleDateString("en-IN")}</TableCell>
                  <TableCell className="text-right font-mono">{r.estimate ? inr0(r.estimate.total) : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function RepairDetailPanel({ id, onBack, custById, chargerById }) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const { data: r, isLoading, isError } = useQuery({
    queryKey: ["repair-admin", id],
    queryFn: async () => (await api.get(`/repairs/${id}`)).data,
    enabled: !!id, retry: false,
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["repair-admin", id] });
    qc.invalidateQueries({ queryKey: ["repairs-all"] });
  };

  const applyStatus = async (target) => {
    setBusy(`status-${target}`);
    try {
      await api.patch(`/repairs/${id}/status`, { status: target });
      toast.success(`Request → ${REPAIR_STATUS_LABEL[target] || target}`);
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not update status");
    } finally { setBusy(null); }
  };

  if (isLoading) return <div className="py-16 text-center"><Loader2 className="h-6 w-6 animate-spin text-charging mx-auto" /></div>;
  if (isError || !r) return <div className="py-16 text-center text-sm text-muted-foreground">Could not load this repair request.</div>;

  const cust = custById[r.user_id];
  const charger = r.charger_id ? chargerById[r.charger_id] : null;
  const nextStatuses = (REPAIR_NEXT[r.status] || []).filter((s) => !CUSTOMER_DECISIONS.includes(s));

  return (
    <div className="space-y-4" data-testid="repair-detail-panel">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" onClick={onBack} data-testid="repair-back-btn" className="rounded-lg"><ArrowLeft className="h-4 w-4 mr-1" /> All repairs</Button>
        <Badge className={`rounded-full ${REPAIR_STATUS_BADGE[r.status] || "bg-secondary text-foreground"}`} data-testid="repair-detail-status">{REPAIR_STATUS_LABEL[r.status] || r.status}</Badge>
      </div>

      <Card className="rounded-xl" data-testid="repair-detail">
        <CardHeader><CardTitle className="font-display text-base flex items-center justify-between">
          <span className="font-mono">{r.repair_request_number}</span>
          <span className="text-xs text-muted-foreground font-normal">Created {new Date(r.created_at).toLocaleString("en-IN")}</span>
        </CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Customer</p>
            <p className="text-sm font-medium">{cust?.name || "Unknown"}</p>
            <p className="text-sm text-muted-foreground font-mono">{cust?.phone || r.user_id}</p>
            <p className="text-xs text-muted-foreground mt-1">{r.customer_type === "STATION_OWNER" ? "Station owner request" : "Retail customer"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Charger</p>
            {r.charger_id ? (
              <>
                <p className="text-sm font-medium font-mono">{r.charger_id}{charger ? ` — ${charger.name}` : ""}</p>
                <button onClick={() => window.open(`/app/charger/${r.charger_id}`, "_blank")} data-testid="repair-charger-link"
                  className="text-xs text-wallet hover:underline mt-0.5">view in customer app</button>
              </>
            ) : (
              <p className="text-sm">{[r.charger_info?.brand, r.charger_info?.model, r.charger_info?.charger_type].filter(Boolean).join(" · ") || "—"} <span className="text-muted-foreground">(unregistered)</span></p>
            )}
            {r.charger_info?.serial_number && <p className="text-xs text-muted-foreground font-mono mt-0.5">SN {r.charger_info.serial_number}</p>}
            {r.charger_info?.power_rating && <p className="text-xs text-muted-foreground">{r.charger_info.power_rating}</p>}
          </div>
          <div className="md:col-span-2">
            <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Problem{r.reported_category ? ` — ${r.reported_category}` : ""}</p>
            <p className="text-sm">{r.problem_description}</p>
            {r.photos?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2" data-testid="repair-photos">
                {r.photos.map((src, i) => <img key={i} src={src} alt={`photo ${i + 1}`} className="h-16 w-16 rounded-lg object-cover border border-border/60" />)}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-xl">
        <CardHeader><CardTitle className="font-display text-base">Workflow</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2" data-testid="repair-status-actions">
            {nextStatuses.length === 0 ? (
              <p className="text-sm text-muted-foreground">No further transitions — this request is closed.</p>
            ) : nextStatuses.map((s) => s === "CANCELLED" ? (
              <Button key={s} size="sm" variant="outline" disabled={!!busy} onClick={() => setConfirmCancel(true)} data-testid={`status-action-${s}`}
                className="rounded-lg text-destructive border-destructive/40 hover:bg-destructive/5"><XCircle className="h-4 w-4 mr-1" /> Cancel request</Button>
            ) : (
              <Button key={s} size="sm" disabled={!!busy || (s === "ESTIMATE_SENT" && !r.estimate)} onClick={() => applyStatus(s)} data-testid={`status-action-${s}`}
                title={s === "ESTIMATE_SENT" && !r.estimate ? "Create an estimate first" : undefined} className="rounded-lg">
                {busy === `status-${s}` && <Loader2 className="h-4 w-4 animate-spin mr-1" />}{REPAIR_STATUS_LABEL[s]}
              </Button>
            ))}
          </div>
          {r.status === "ESTIMATE_SENT" && (
            <p className="text-sm text-amber-600 flex items-center gap-2" data-testid="awaiting-customer-note">
              <Info className="h-4 w-4" /> Awaiting customer decision — they approve or decline from their repair page.
            </p>
          )}
          <div>
            <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Status history</p>
            <div className="space-y-1">
              {(r.status_history || []).slice().reverse().map((h, i) => (
                <div key={i} className="flex items-center justify-between text-sm border-b border-border/40 pb-1 last:border-0">
                  <span className="font-medium">{REPAIR_STATUS_LABEL[h.status] || h.status}</span>
                  <span className="text-xs text-muted-foreground font-mono">{new Date(h.at).toLocaleString("en-IN")}{h.note ? ` · ${h.note}` : ""}</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {["REPAIR_COMPLETED", "PAYMENT_PENDING"].includes(r.status) && <RepairPaymentVerification key={r.id} repair={r} onSaved={refresh} />}
      {r.payment_summary && <RepairPaymentPanel key={`payment-${r.id}`} repairId={r.id} admin repairStatus={r.status} refreshToken={r.updated_at} />}

      <DiagnosisCard r={r} busy={busy} setBusy={setBusy} onSaved={refresh} />
      <EstimateCard r={r} busy={busy} setBusy={setBusy} onSaved={refresh} onSend={() => applyStatus("ESTIMATE_SENT")} />

      <Card className="rounded-xl">
        <CardHeader><CardTitle className="font-display text-base">Shipments</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <ShipmentCard r={r} leg="incoming" busy={busy} setBusy={setBusy} onSaved={refresh} />
          <ShipmentCard r={r} leg="return" busy={busy} setBusy={setBusy} onSaved={refresh} />
        </CardContent>
      </Card>

      <AlertDialog open={confirmCancel} onOpenChange={setConfirmCancel}>
        <AlertDialogContent data-testid="repair-cancel-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display">Cancel repair request?</AlertDialogTitle>
            <AlertDialogDescription>Request {r.repair_request_number} will be closed. This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="repair-cancel-dismiss">Keep request</AlertDialogCancel>
            <AlertDialogAction onClick={() => { setConfirmCancel(false); applyStatus("CANCELLED"); }} disabled={!!busy} data-testid="repair-cancel-confirm"
              className="bg-destructive text-white hover:bg-destructive/90">
              {busy === "status-CANCELLED" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Cancel request"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function DiagnosisCard({ r, busy, setBusy, onSaved }) {
  const [f, setF] = useState({
    diagnosis: r.diagnosis?.diagnosis || "",
    identified_fault: r.diagnosis?.identified_fault || "",
    repairability: r.diagnosis?.repairability || "UNKNOWN",
    parts_required: (r.diagnosis?.parts_required || []).join(", "),
    technician_notes: r.diagnosis?.technician_notes || "",
    internal_notes: r.diagnosis?.internal_notes || "",
  });
  const save = async () => {
    setBusy("diagnosis");
    try {
      await api.patch(`/repairs/${r.id}/diagnosis`, {
        diagnosis: f.diagnosis || undefined,
        identified_fault: f.identified_fault || undefined,
        repairability: f.repairability || undefined,
        parts_required: f.parts_required.trim() ? f.parts_required.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
        technician_notes: f.technician_notes || undefined,
        internal_notes: f.internal_notes || undefined,
      });
      toast.success("Diagnosis saved");
      onSaved();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not save diagnosis");
    } finally { setBusy(null); }
  };
  return (
    <Card className="rounded-xl" data-testid="diagnosis-card">
      <CardHeader><CardTitle className="font-display text-base flex items-center gap-2">Diagnosis
        <Badge className="rounded-full bg-amber-500/15 text-amber-600">RushX team</Badge>
      </CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">Summary, fault and repairability are visible to the customer. Fields marked <span className="text-amber-600">internal</span> are stripped by the API for non-admin users.</p>
        <div className="space-y-1.5">
          <Label>Diagnosis summary <span className="text-muted-foreground">(visible to customer)</span></Label>
          <Textarea data-testid="diagnosis-input" value={f.diagnosis} onChange={(e) => setF({ ...f, diagnosis: e.target.value })} rows={2} placeholder="What is wrong with the charger" />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Identified fault <span className="text-muted-foreground">(visible)</span></Label>
            <Input data-testid="diagnosis-fault-input" value={f.identified_fault} onChange={(e) => setF({ ...f, identified_fault: e.target.value })} className="h-10" placeholder="e.g. PCB fault" />
          </div>
          <div className="space-y-1.5">
            <Label>Repairability <span className="text-muted-foreground">(visible)</span></Label>
            <Select value={f.repairability} onValueChange={(v) => setF({ ...f, repairability: v })}>
              <SelectTrigger data-testid="diagnosis-repairability" className="h-10"><SelectValue /></SelectTrigger>
              <SelectContent>{["UNKNOWN", "REPAIRABLE", "NOT_REPAIRABLE"].map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Parts required <span className="text-amber-600">(internal)</span></Label>
          <Input data-testid="diagnosis-parts" value={f.parts_required} onChange={(e) => setF({ ...f, parts_required: e.target.value })} className="h-10 font-mono" placeholder="Comma-separated, e.g. PCB, MOSFET" />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Technician notes <span className="text-amber-600">(internal)</span></Label>
            <Textarea data-testid="diagnosis-tech-notes" value={f.technician_notes} onChange={(e) => setF({ ...f, technician_notes: e.target.value })} rows={2} />
          </div>
          <div className="space-y-1.5">
            <Label>Internal notes <span className="text-amber-600">(internal)</span></Label>
            <Textarea data-testid="diagnosis-internal-notes" value={f.internal_notes} onChange={(e) => setF({ ...f, internal_notes: e.target.value })} rows={2} />
          </div>
        </div>
        <Button onClick={save} disabled={!!busy} data-testid="diagnosis-save-btn" className="rounded-lg">
          {busy === "diagnosis" && <Loader2 className="h-4 w-4 animate-spin mr-1" />} Save diagnosis
        </Button>
      </CardContent>
    </Card>
  );
}

function EstimateCard({ r, busy, setBusy, onSaved, onSend }) {
  const e = r.estimate;
  const [open, setOpen] = useState(false);
  const [confirmSend, setConfirmSend] = useState(false);
  const [f, setF] = useState(() => ({
    parts: e?.parts?.length ? e.parts.map((p) => ({ name: p.name || "", qty: String(p.qty ?? 1), price: String(p.price ?? 0) })) : [{ name: "", qty: "1", price: "0" }],
    labor: e?.labor != null ? String(e.labor) : "0",
    diagnostic_fee: e?.diagnostic_fee != null ? String(e.diagnostic_fee) : "0",
    incoming_logistics_cost: e?.incoming_logistics_cost != null ? String(e.incoming_logistics_cost) : "0",
    return_shipping_cost: e?.return_shipping_cost != null ? String(e.return_shipping_cost) : "0",
    other_charges: e?.other_charges != null ? String(e.other_charges) : "0",
    tax: e?.tax != null ? String(e.tax) : "0",
    notes: e?.notes || "",
  }));
  const setPart = (i, k, v) => setF({ ...f, parts: f.parts.map((p, j) => (j === i ? { ...p, [k]: v } : p)) });
  const save = async () => {
    setBusy("estimate");
    try {
      await api.patch(`/repairs/${r.id}/estimate`, {
        parts: f.parts.filter((p) => p.name.trim()).map((p) => ({ name: p.name.trim(), qty: Number(p.qty) || 1, price: Number(p.price) || 0 })),
        labor: Number(f.labor) || 0,
        diagnostic_fee: Number(f.diagnostic_fee) || 0,
        incoming_logistics_cost: Number(f.incoming_logistics_cost) || 0,
        return_shipping_cost: Number(f.return_shipping_cost) || 0,
        other_charges: Number(f.other_charges) || 0,
        tax: Number(f.tax) || 0,
        notes: f.notes || undefined,
      });
      toast.success("Estimate saved — totals calculated by the server");
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not save estimate");
    } finally { setBusy(null); }
  };
  return (
    <Card className="rounded-xl" data-testid="estimate-card">
      <CardHeader><CardTitle className="font-display text-base flex items-center justify-between">Estimate
        {e && <Badge className={`rounded-full ${e.status === "APPROVED" ? "bg-charging/15 text-charging" : e.status === "DECLINED" ? "bg-destructive/15 text-destructive" : "bg-secondary text-foreground"}`} data-testid="estimate-status">{e.status}</Badge>}
      </CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {e?.status === "APPROVED" && (
          <p className="text-sm text-charging" data-testid="customer-decision">Customer approved{e.approved_at ? ` on ${new Date(e.approved_at).toLocaleString("en-IN")}` : ""} — proceed with the repair.</p>
        )}
        {e?.status === "DECLINED" && (
          <p className="text-sm text-destructive" data-testid="customer-decision">Customer declined{e.declined_at ? ` on ${new Date(e.declined_at).toLocaleString("en-IN")}` : ""} — arrange return shipment.</p>
        )}
        {e?.status === "SENT" && <p className="text-sm text-amber-600" data-testid="customer-decision">Sent to customer — awaiting their decision.</p>}
        {e?.status === "DRAFT" && <p className="text-sm text-muted-foreground" data-testid="customer-decision">Draft — not yet sent to the customer.</p>}
        {!open && e && (
          <div className="rounded-xl border border-border/60 p-4 space-y-1.5 text-sm" data-testid="estimate-summary">
            {(e.parts || []).map((p, i) => (
              <div key={i} className="flex items-center justify-between"><span className="text-muted-foreground">{p.name}{p.qty > 1 ? ` × ${p.qty}` : ""}</span><span className="font-mono">{inr((p.price || 0) * (p.qty || 1))}</span></div>
            ))}
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Labor</span><span className="font-mono">{inr(e.labor || 0)}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Diagnostic fee</span><span className="font-mono">{inr(e.diagnostic_fee || 0)}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Incoming logistics</span><span className="font-mono">{inr(e.incoming_logistics_cost || 0)}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Return shipping</span><span className="font-mono">{inr(e.return_shipping_cost || 0)}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Other charges</span><span className="font-mono">{inr(e.other_charges || 0)}</span></div>
            <div className="flex items-center justify-between border-t border-border/60 pt-2"><span className="text-muted-foreground">Subtotal</span><span className="font-mono" data-testid="estimate-subtotal">{inr(e.subtotal)}</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Tax</span><span className="font-mono" data-testid="estimate-tax">{inr(e.tax || 0)}</span></div>
            <div className="flex items-center justify-between border-t border-border/60 pt-2"><span className="font-medium">Total</span><span className="font-mono font-semibold" data-testid="estimate-total">{inr(e.total)}</span></div>
            {e.notes && <p className="text-xs text-muted-foreground pt-1">{e.notes}</p>}
          </div>
        )}
        {!e && !open && <p className="text-sm text-muted-foreground">No estimate yet. Add one after diagnosing the charger.</p>}
        {open && (
          <div className="space-y-3" data-testid="estimate-form">
            <div className="space-y-2">
              <Label>Parts</Label>
              {f.parts.map((p, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input data-testid={`estimate-part-name-${i}`} placeholder="Part name" value={p.name} onChange={(ev) => setPart(i, "name", ev.target.value)} className="h-10 flex-1" />
                  <Input data-testid={`estimate-part-qty-${i}`} type="number" min="1" placeholder="Qty" value={p.qty} onChange={(ev) => setPart(i, "qty", ev.target.value)} className="h-10 w-20" />
                  <Input data-testid={`estimate-part-price-${i}`} type="number" min="0" placeholder="Price" value={p.price} onChange={(ev) => setPart(i, "price", ev.target.value)} className="h-10 w-28 font-mono" />
                  <Button size="icon" variant="outline" onClick={() => setF({ ...f, parts: f.parts.filter((_, j) => j !== i) })} data-testid={`estimate-part-remove-${i}`} className="h-10 w-10 shrink-0"><Trash2 className="h-4 w-4" /></Button>
                </div>
              ))}
              <Button size="sm" variant="outline" onClick={() => setF({ ...f, parts: [...f.parts, { name: "", qty: "1", price: "0" }] })} data-testid="estimate-part-add" className="rounded-lg"><Plus className="h-4 w-4 mr-1" /> Add part</Button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[["labor", "Labor"], ["diagnostic_fee", "Diagnostic fee"], ["incoming_logistics_cost", "Incoming logistics"], ["return_shipping_cost", "Return shipping"], ["other_charges", "Other charges"], ["tax", "Tax"]].map(([k, label]) => (
                <div key={k} className="space-y-1.5">
                  <Label>{label}</Label>
                  <Input data-testid={`estimate-${k}`} type="number" min="0" value={f[k]} onChange={(ev) => setF({ ...f, [k]: ev.target.value })} className="h-10 font-mono" />
                </div>
              ))}
            </div>
            <div className="space-y-1.5">
              <Label>Notes <span className="text-muted-foreground">(visible to customer)</span></Label>
              <Input data-testid="estimate-notes" value={f.notes} onChange={(ev) => setF({ ...f, notes: ev.target.value })} className="h-10" />
            </div>
            <p className="text-xs text-muted-foreground">Subtotal and total are calculated by the backend on save.</p>
            <div className="flex gap-2">
              <Button onClick={save} disabled={!!busy} data-testid="estimate-save-btn" className="rounded-lg">{busy === "estimate" && <Loader2 className="h-4 w-4 animate-spin mr-1" />} Save estimate</Button>
              <Button variant="outline" onClick={() => setOpen(false)} data-testid="estimate-close-btn" className="rounded-lg">Close</Button>
            </div>
          </div>
        )}
        {!open && (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setOpen(true)} disabled={!!e && e.status !== "DRAFT"} title={e && e.status !== "DRAFT" ? "Published estimates are locked; contact support for a revised quote" : undefined} data-testid="estimate-toggle-btn" className="rounded-lg">{e ? "Edit estimate" : "Create estimate"}</Button>
          </div>
        )}
        {r.status === "DIAGNOSING" && e && (
          <Button onClick={() => setConfirmSend(true)} disabled={!!busy} data-testid="send-estimate-btn" className="rounded-lg bg-wallet text-white hover:bg-wallet/90">
            {busy === "status-ESTIMATE_SENT" ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />} Send estimate to customer
          </Button>
        )}
        <AlertDialog open={confirmSend} onOpenChange={setConfirmSend}>
          <AlertDialogContent data-testid="send-estimate-dialog">
            <AlertDialogHeader>
              <AlertDialogTitle className="font-display">Send estimate to customer?</AlertDialogTitle>
              <AlertDialogDescription>
                The estimate ({inr(e?.total || 0)}) will be sent to the customer for approval or decline. No payment is collected at this step.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel data-testid="send-estimate-dismiss">Not yet</AlertDialogCancel>
              <AlertDialogAction onClick={() => { setConfirmSend(false); onSend(); }} disabled={!!busy} data-testid="send-estimate-confirm" className="bg-wallet text-white hover:bg-wallet/90">
                {busy === "status-ESTIMATE_SENT" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send estimate"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  );
}

function ShipmentCard({ r, leg, busy, setBusy, onSaved }) {
  const s = r[leg === "incoming" ? "incoming_shipment" : "return_shipment"] || {};
  const [f, setF] = useState({
    courier: s.courier || "",
    tracking_number: s.tracking_number || "",
    shipped_date: s.shipped_date || "",
    received_date: s.received_date || "",
    delivered_date: s.delivered_date || "",
    notes: s.notes || "",
  });
  const save = async () => {
    setBusy(`shipment-${leg}`);
    try {
      await api.patch(`/repairs/${r.id}/shipment`, {
        leg,
        courier: f.courier || undefined,
        tracking_number: f.tracking_number || undefined,
        shipped_date: f.shipped_date || undefined,
        received_date: f.received_date || undefined,
        delivered_date: f.delivered_date || undefined,
        notes: f.notes || undefined,
      });
      toast.success(`${leg === "incoming" ? "Incoming" : "Return"} shipment saved`);
      onSaved();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not save shipment details");
    } finally { setBusy(null); }
  };
  const shown = [s.courier, s.tracking_number, s.shipped_date, leg === "incoming" ? s.received_date : s.delivered_date].filter(Boolean);
  return (
    <div className="rounded-xl border border-border/60 p-4 space-y-2" data-testid={`shipment-${leg}`}>
      <p className="text-xs uppercase tracking-widest text-muted-foreground">{leg === "incoming" ? "Incoming — customer → RushX" : "Return — RushX → customer"}</p>
      {shown.length > 0 && <p className="text-sm font-mono">{shown.join(" · ")}</p>}
      <div className="grid grid-cols-2 gap-2">
        <Input data-testid={`shipment-${leg}-courier`} placeholder="Courier" value={f.courier} onChange={(e) => setF({ ...f, courier: e.target.value })} className="h-10" />
        <Input data-testid={`shipment-${leg}-tracking`} placeholder="Tracking no." value={f.tracking_number} onChange={(e) => setF({ ...f, tracking_number: e.target.value })} className="h-10 font-mono" />
        <Input data-testid={`shipment-${leg}-shipped`} type="date" value={f.shipped_date} onChange={(e) => setF({ ...f, shipped_date: e.target.value })} className="h-10" />
        {leg === "incoming" ? (
          <Input data-testid={`shipment-${leg}-received`} type="date" value={f.received_date} onChange={(e) => setF({ ...f, received_date: e.target.value })} className="h-10" />
        ) : (
          <Input data-testid={`shipment-${leg}-delivered`} type="date" value={f.delivered_date} onChange={(e) => setF({ ...f, delivered_date: e.target.value })} className="h-10" />
        )}
      </div>
      <Input data-testid={`shipment-${leg}-notes`} placeholder="Notes" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} className="h-10" />
      <Button size="sm" onClick={save} disabled={!!busy} data-testid={`shipment-${leg}-save-btn`} className="rounded-lg">
        {busy === `shipment-${leg}` && <Loader2 className="h-4 w-4 animate-spin mr-1" />} Save
      </Button>
    </div>
  );
}
