import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Wrench, ArrowLeft, ArrowRight, Loader2, Server, PackagePlus, X,
  Camera, ShieldCheck, CheckCircle2, Info, FileText, MapPin,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const TYPE_OPTIONS = [
  { label: "AC Charger", value: "AC" },
  { label: "DC Charger", value: "DC" },
  { label: "Portable EV Charger", value: "PORTABLE" },
  { label: "Other", value: "OTHER" },
  { label: "Not sure", value: "NOT_SURE" },
];
const CATEGORIES = [
  "Not powering on", "Not charging", "Charging intermittently", "Charging stops unexpectedly",
  "Error / Fault displayed", "Cable or connector damaged", "Physical damage", "Overheating", "Other", "Not sure",
];
const MAX_PHOTOS = 5;
const MAX_MB = 5;

export default function RepairNew() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [source, setSource] = useState("other");
  const [chargerId, setChargerId] = useState("");
  const [info, setInfo] = useState({ brand: "", model: "", charger_type: "", serial_number: "", power_rating: "", purchase_date: "" });
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const { data: myChargers = [] } = useQuery({
    queryKey: ["my-chargers"],
    queryFn: async () => (user?.role === "owner" || user?.role === "admin") ? (await api.get("/owner/chargers")).data : [],
  });

  const selected = useMemo(() => myChargers.find((c) => c.charger_id === chargerId), [myChargers, chargerId]);

  const onFiles = (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    for (const f of files) {
      if (!f.type.startsWith("image/")) { toast.error(`${f.name}: not an image`); continue; }
      if (f.size > MAX_MB * 1024 * 1024) { toast.error(`${f.name}: exceeds ${MAX_MB}MB`); continue; }
      if (photos.length >= MAX_PHOTOS) { toast.error(`Max ${MAX_PHOTOS} photos`); break; }
      const reader = new FileReader();
      reader.onload = () => setPhotos((p) => (p.length >= MAX_PHOTOS ? p : [...p, { name: f.name, data: reader.result }]));
      reader.onerror = () => toast.error(`${f.name}: failed to read file`);
      reader.readAsDataURL(f);
    }
  };

  const validate = () => {
    if (source === "mine" && !chargerId) return "Please select one of your chargers";
    if (source === "other") {
      if (!info.brand.trim()) return "Manufacturer / Brand is required";
      if (!info.model.trim()) return "Model is required";
      if (!info.charger_type) return "Please select a charger type";
    }
    if (!description.trim()) return "Please describe the problem";
    return null;
  };

  const submit = async () => {
    const err = validate();
    if (err) { toast.error(err); return; }
    setSubmitting(true);
    try {
      const payload = {
        customer_type: user?.role === "owner" ? "STATION_OWNER" : "RETAIL",
        problem_description: description.trim(),
        reported_category: category || null,
        photos: photos.map((p) => p.data),
      };
      if (source === "mine") {
        payload.charger_id = chargerId;
      } else {
        payload.charger_info = {
          brand: info.brand.trim(), model: info.model.trim(),
          charger_type: info.charger_type === "NOT_SURE" ? null : info.charger_type,
          serial_number: info.serial_number.trim() || null,
          power_rating: info.power_rating.trim() || null,
          purchase_date: info.purchase_date || null,
        };
      }
      const { data } = await api.post("/repairs", payload);
      // Advance to AWAITING_SHIPMENT via validated Phase 1 transition (non-fatal if it fails)
      try { await api.patch(`/repairs/${data.id}/status`, { status: "AWAITING_SHIPMENT" }); }
      catch { toast.message("Repair request created. Shipment status will update shortly."); }
      setResult({ id: data.id, number: data.repair_request_number });
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not submit repair request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // ---------- Confirmation ----------
  if (result) {
    return (
      <CustomerShell>
        <div className="p-4 lg:p-8 max-w-xl mx-auto" data-testid="repair-confirmation">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-center">
            <div className="mx-auto h-16 w-16 rounded-full bg-charging/15 flex items-center justify-center"><CheckCircle2 className="h-9 w-9 text-charging" /></div>
            <h1 className="mt-5 font-display text-2xl font-semibold tracking-tight">Repair Request Submitted</h1>
            <p className="mt-2 text-muted-foreground">Your repair request has been created.</p>
            <div className="mt-5 inline-flex items-center gap-2 rounded-xl border border-border/60 px-5 py-3">
              <FileText className="h-5 w-5 text-charging" />
              <span className="font-mono text-lg font-semibold" data-testid="repair-number">Repair Request: {result.number}</span>
            </div>
          </motion.div>

          <div className="mt-6 rounded-2xl border border-border/60 p-5 space-y-4 text-sm">
            <div className="flex gap-3"><MapPin className="h-5 w-5 text-muted-foreground shrink-0" /><div><p className="font-medium">Send your charger to the Voltx service center</p><p className="text-muted-foreground mt-0.5">Shipping instructions will be provided by the Voltx service team.</p></div></div>
            <div className="flex gap-3"><Info className="h-5 w-5 text-muted-foreground shrink-0" /><p className="text-muted-foreground">Please include your repair request number <span className="font-mono text-foreground">{result.number}</span> with the charger.</p></div>
            <div className="flex gap-3"><ShieldCheck className="h-5 w-5 text-charging shrink-0" /><p className="text-muted-foreground">Payment is not required at this stage.</p></div>
          </div>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Button onClick={() => navigate(`/repairs/${result.id}`)} data-testid="view-repair-btn" className="h-12 rounded-lg">View Repair Request</Button>
            <Button variant="outline" onClick={() => navigate("/app")} data-testid="back-dashboard-btn" className="h-12 rounded-lg">Back to Dashboard</Button>
          </div>
        </div>
      </CustomerShell>
    );
  }

  // ---------- Form ----------
  return (
    <CustomerShell>
      <div className="p-4 lg:p-8 max-w-2xl mx-auto" data-testid="repair-new-page">
        <button onClick={() => navigate("/app")} data-testid="repair-back-btn" className="flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 mb-4"><ArrowLeft className="h-4 w-4 mr-1" /> Back</button>

        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-xl bg-charging/10 flex items-center justify-center"><Wrench className="h-6 w-6 text-charging" /></div>
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight">Repair a Charger</h1>
            <p className="text-sm text-muted-foreground">Get your EV charger diagnosed and repaired by the Voltx service team.</p>
          </div>
        </div>
        <div className="mt-4 rounded-xl bg-secondary/50 border border-border/60 px-4 py-3 text-sm flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-charging shrink-0" />
          <span>We repair EV chargers of <b>any brand</b> — retail &amp; station chargers, AC, DC and portable.</span>
        </div>

        {/* 1. Source */}
        <section className="mt-8">
          <h2 className="font-display font-semibold mb-3">Which charger needs repair?</h2>
          <div className="grid grid-cols-2 gap-3">
            {[{ v: "mine", icon: Server, t: "My Voltx Charger", d: "Select a registered charger" }, { v: "other", icon: PackagePlus, t: "Other Charger", d: "Any brand, not on Voltx" }].map((o) => (
              <button key={o.v} onClick={() => setSource(o.v)} data-testid={`source-${o.v}`}
                className={`rounded-xl border p-4 text-left transition-colors duration-200 ${source === o.v ? "border-charging bg-charging/5" : "border-border/60 hover:bg-secondary/50"}`}>
                <o.icon className={`h-6 w-6 ${source === o.v ? "text-charging" : "text-muted-foreground"}`} strokeWidth={1.5} />
                <p className="font-medium mt-2">{o.t}</p><p className="text-xs text-muted-foreground">{o.d}</p>
              </button>
            ))}
          </div>
        </section>

        {/* 2. Charger details */}
        <section className="mt-8">
          <h2 className="font-display font-semibold mb-3">Charger details</h2>
          {source === "mine" ? (
            <div className="space-y-3">
              {myChargers.length === 0 ? (
                <div className="rounded-xl border border-border/60 p-4 text-sm text-muted-foreground">
                  No registered chargers found on your account. Choose <button className="text-charging font-medium" onClick={() => setSource("other")}>Other Charger</button> to continue.
                </div>
              ) : (
                <>
                  <Label>Select your charger</Label>
                  <Select value={chargerId} onValueChange={setChargerId}>
                    <SelectTrigger data-testid="my-charger-select" className="h-11"><SelectValue placeholder="Choose a charger" /></SelectTrigger>
                    <SelectContent>{myChargers.map((c) => <SelectItem key={c.charger_id} value={c.charger_id}>{c.charger_id} — {c.name}</SelectItem>)}</SelectContent>
                  </Select>
                  {selected && (
                    <div className="rounded-xl border border-border/60 p-4 grid grid-cols-2 gap-y-2 text-sm" data-testid="selected-charger-info">
                      <span className="text-muted-foreground">Charger</span><span className="text-right font-medium">{selected.name}</span>
                      <span className="text-muted-foreground">Connector</span><span className="text-right">{selected.connector}</span>
                      <span className="text-muted-foreground">Power</span><span className="text-right">{selected.max_power_kw} kW</span>
                      <span className="text-muted-foreground">Location</span><span className="text-right">{selected.location || "—"}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-1.5"><Label>Manufacturer / Brand *</Label><Input data-testid="brand-input" value={info.brand} onChange={(e) => setInfo({ ...info, brand: e.target.value })} placeholder="e.g. Delta, ABB, Tata Power" className="h-11" /></div>
              <div className="space-y-1.5"><Label>Model *</Label><Input data-testid="model-input" value={info.model} onChange={(e) => setInfo({ ...info, model: e.target.value })} placeholder="e.g. AC Mini 7.4" className="h-11" /></div>
              <div className="space-y-1.5">
                <Label>Charger Type *</Label>
                <Select value={info.charger_type} onValueChange={(v) => setInfo({ ...info, charger_type: v })}>
                  <SelectTrigger data-testid="type-select" className="h-11"><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>{TYPE_OPTIONS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Serial Number</Label><Input data-testid="serial-input" value={info.serial_number} onChange={(e) => setInfo({ ...info, serial_number: e.target.value })} placeholder="Optional" className="h-11" /></div>
              <div className="space-y-1.5"><Label>Power Rating</Label><Input data-testid="power-input" value={info.power_rating} onChange={(e) => setInfo({ ...info, power_rating: e.target.value })} placeholder="e.g. 7.4 kW (optional)" className="h-11" /></div>
              <div className="space-y-1.5"><Label>Purchase Date</Label><Input data-testid="purchase-input" type="date" value={info.purchase_date} onChange={(e) => setInfo({ ...info, purchase_date: e.target.value })} className="h-11" /></div>
            </div>
          )}
        </section>

        {/* 3. Problem */}
        <section className="mt-8">
          <h2 className="font-display font-semibold mb-3">{"What's wrong with your charger?"}</h2>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Problem category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger data-testid="category-select" className="h-11"><SelectValue placeholder="Select a category" /></SelectTrigger>
                <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Describe the problem *</Label>
              <Textarea data-testid="description-input" value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="Please describe what happens when you try to use the charger..." />
            </div>
          </div>
        </section>

        {/* 4. Photos */}
        <section className="mt-8">
          <h2 className="font-display font-semibold mb-1">Photos <span className="text-sm font-normal text-muted-foreground">(optional)</span></h2>
          <p className="text-xs text-muted-foreground mb-3">Helpful: front & back of charger, rating label, connector/cable, and any visible damage. Max {MAX_PHOTOS} images, {MAX_MB}MB each.</p>
          <div className="flex flex-wrap gap-3">
            {photos.map((p, i) => (
              <div key={i} className="relative h-20 w-20 rounded-lg overflow-hidden border border-border/60" data-testid={`photo-${i}`}>
                <img src={p.data} alt={p.name} className="h-full w-full object-cover" />
                <button onClick={() => setPhotos(photos.filter((_, idx) => idx !== i))} data-testid={`remove-photo-${i}`} className="absolute top-0.5 right-0.5 h-5 w-5 rounded-full bg-black/60 text-white flex items-center justify-center"><X className="h-3 w-3" /></button>
              </div>
            ))}
            {photos.length < MAX_PHOTOS && (
              <label data-testid="photo-upload" className="h-20 w-20 rounded-lg border-2 border-dashed border-border flex flex-col items-center justify-center gap-1 text-muted-foreground cursor-pointer hover:border-charging transition-colors duration-200">
                <Camera className="h-5 w-5" /><span className="text-[10px]">Add</span>
                <input type="file" accept="image/*" multiple className="hidden" onChange={onFiles} data-testid="photo-input" />
              </label>
            )}
          </div>
        </section>

        {/* 5. Review */}
        <section className="mt-8">
          <h2 className="font-display font-semibold mb-3">Review</h2>
          <div className="rounded-xl border border-border/60 p-4 space-y-3 text-sm" data-testid="review-section">
            <div>
              <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Charger</p>
              {source === "mine" ? (
                <p>{selected ? `${selected.charger_id} — ${selected.name}` : <span className="text-muted-foreground">No charger selected</span>}</p>
              ) : (
                <p>{info.brand || "—"} {info.model && `· ${info.model}`} {info.charger_type && `· ${TYPE_OPTIONS.find((t) => t.value === info.charger_type)?.label}`} {info.serial_number && `· SN: ${info.serial_number}`}</p>
              )}
            </div>
            <div><p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Problem</p><p>{category || "—"}{description ? ` — ${description}` : ""}</p></div>
            <div><p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Photos</p><p>{photos.length} uploaded</p></div>
          </div>
        </section>

        {/* 6. Payment note */}
        <div className="mt-6 rounded-xl bg-charging/5 border border-charging/30 p-4 text-sm">
          <p className="font-medium flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-charging shrink-0" /> No payment is required to submit a repair request.</p>
          <p className="text-muted-foreground mt-1">Once we receive and diagnose your charger, we will provide a repair estimate for your approval before any repair work is carried out.</p>
        </div>

        <Button onClick={submit} disabled={submitting} data-testid="submit-repair-btn" className="w-full h-12 mt-6 rounded-lg text-base">
          {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <>Submit repair request <ArrowRight className="h-4 w-4 ml-2" /></>}
        </Button>
      </div>
    </CustomerShell>
  );
}
