import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Wrench, ArrowLeft, ArrowRight, Loader2, Server, PackagePlus, X,
  Camera, ShieldCheck, CheckCircle2, FileText,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { CustomerShell } from "../../components/layout/CustomerShell";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

import "./RepairNew.css";

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
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [source, setSource] = useState("other");
  const [chargerId, setChargerId] = useState("");
  const [info, setInfo] = useState({ brand: "", model: "", charger_type: "", serial_number: "", power_rating: "", purchase_date: "" });
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState({});
  const submissionLock = useRef(false);
  const clearError = (key, value) => {
    if (value.trim()) setErrors((current) => ({ ...current, [key]: undefined }));
  };
  const updateInfo = (key, value) => {
    setInfo((current) => ({ ...current, [key]: value }));
    clearError(key, value);
  };
  const chooseSource = (value) => { setSource(value); setErrors({}); };
  const fieldProps = (key, helper) => ({
    id: key,
    "aria-invalid": Boolean(errors[key]),
    "aria-describedby": [helper, errors[key] && `${key}-error`].filter(Boolean).join(" ") || undefined,
  });
  const fieldError = (key) => errors[key] && <p id={`${key}-error`} role="alert" className="text-sm font-medium text-destructive">{errors[key]}</p>;

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

  const submit = async (event) => {
    event.preventDefault();
    if (submissionLock.current) return;
    const nextErrors = {};
    if (source === "mine" && !chargerId) nextErrors.chargerId = "Please select one of your chargers";
    if (source === "other") {
      if (!info.brand.trim()) nextErrors.brand = "Brand is required";
      if (!info.model.trim()) nextErrors.model = "Model is required";
      if (!info.charger_type) nextErrors.charger_type = "Please select a charger type";
    }
    if (!description.trim()) nextErrors.description = "Please describe the problem";
    setErrors(nextErrors);
    const firstInvalid = Object.keys(nextErrors)[0];
    if (firstInvalid) {
      const control = document.getElementById(firstInvalid);
      control?.focus();
      control?.scrollIntoView?.({ behavior: "smooth", block: "center" });
      return;
    }
    submissionLock.current = true;
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
      queryClient.invalidateQueries({ queryKey: ["repairs-mine"] });
      setResult({ id: data.id, number: data.repair_request_number });
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not submit repair request. Please try again.");
    } finally {
      submissionLock.current = false;
      setSubmitting(false);
    }
  };

  if (result) {
    return <CustomerShell>
      <div className="repair-form p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto" data-testid="repair-confirmation">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <CheckCircle2 className="mx-auto h-14 w-14 text-charging" aria-hidden="true" />
          <h1 className="mt-5 font-display text-3xl font-semibold tracking-tight">Repair Request Submitted</h1>
          <p className="mt-3 text-base text-muted-foreground">We’ve received your request.</p>
          <div className="mt-6 rounded-xl border border-border p-5">
            <p className="text-sm text-muted-foreground">Repair request number</p>
            <p className="mt-2 font-mono text-xl font-semibold break-words" data-testid="repair-number"><FileText className="inline h-5 w-5 mr-2" aria-hidden="true" />{result.number}</p>
          </div>
        </motion.div>
        <section className="mt-8">
          <h2 className="text-xl font-semibold">What happens next</h2>
          <ol className="mt-4 list-decimal pl-6 space-y-4 text-base leading-relaxed">
            <li>We’ve received your request.</li>
            <li>Send the charger to the Voltx service center. <span className="text-muted-foreground">Our service team will provide shipping instructions.</span></li>
            <li>Include the repair request number with the package.</li>
            <li>We’ll update you once the charger is received.</li>
            <li>You’ll receive a repair estimate for approval before any paid work begins.</li>
          </ol>
        </section>
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Button onClick={() => navigate(`/repairs/${result.id}`)} data-testid="view-repair-btn" className="h-[52px] text-base">View Repair Request</Button>
          <Button variant="outline" onClick={() => navigate("/app")} data-testid="back-dashboard-btn" className="h-[52px] text-base">Back to Dashboard</Button>
        </div>
      </div>
    </CustomerShell>;
  }

  return <CustomerShell>
    <div className="repair-form p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto" data-testid="repair-new-page">
      <button type="button" onClick={() => navigate("/app")} data-testid="repair-back-btn" className="min-h-11 flex items-center gap-2 text-base text-muted-foreground hover:text-foreground mb-4"><ArrowLeft className="h-4 w-4" />Back</button>
      <div className="flex items-start gap-3">
        <div className="h-12 w-12 shrink-0 rounded-xl bg-charging/10 flex items-center justify-center"><Wrench className="h-6 w-6 text-charging" aria-hidden="true" /></div>
        <div className="min-w-0"><h1 className="font-display text-3xl font-semibold tracking-tight">Repair a charger</h1>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground">Tell us what’s wrong with your charger.<br />We’ll diagnose it and keep you updated through the repair process.</p></div>
      </div>
      <div className="mt-6 rounded-xl bg-secondary/50 border border-border p-5 flex items-start gap-3">
        <ShieldCheck className="h-6 w-6 text-charging shrink-0" aria-hidden="true" />
        <div><p className="text-base font-semibold">We repair EV chargers from any brand</p><p className="mt-2 text-base leading-relaxed text-muted-foreground">Home chargers, station chargers, AC, DC and portable chargers are supported.</p></div>
      </div>
      <form onSubmit={submit} noValidate>
        <p className="mt-6 text-sm text-muted-foreground">Fields marked * are required. Everything else is optional.</p>
        <section className="repair-section" aria-labelledby="source-heading">
          <h2 id="source-heading">1. Choose your charger</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[{ v: "mine", icon: Server, t: "My Voltx charger", d: "Choose a charger already linked to your account" }, { v: "other", icon: PackagePlus, t: "Other charger", d: "Repair a charger from any brand" }].map((o) => (
              <button type="button" key={o.v} onClick={() => chooseSource(o.v)} aria-pressed={source === o.v} data-testid={`source-${o.v}`}
                className={`rounded-xl border-2 p-5 text-left transition-colors ${source === o.v ? "border-charging bg-charging/10" : "border-border hover:bg-secondary/50"}`}>
                <div className="flex justify-between"><o.icon className={`h-6 w-6 ${source === o.v ? "text-charging" : "text-muted-foreground"}`} aria-hidden="true" />{source === o.v && <CheckCircle2 className="h-5 w-5 text-charging" aria-hidden="true" />}</div>
                <p className="text-base font-semibold mt-3">{o.t}</p><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{o.d}</p>
              </button>
            ))}
          </div>
        </section>
        <section className="repair-section" aria-labelledby="details-heading">
          <h2 id="details-heading">2. Charger details</h2>
          {source === "mine" ? <div className="space-y-4">
            {myChargers.length === 0 ? <div className="rounded-xl border border-border p-5 text-base text-muted-foreground">
              No registered chargers found on your account. <button id="chargerId" type="button" {...fieldProps("chargerId")} className="underline font-medium min-h-11 text-foreground" onClick={() => chooseSource("other")}>Choose Other charger</button> to continue.
              {fieldError("chargerId")}
            </div> : <>
              <Label htmlFor="chargerId">Select your charger *</Label>
              <Select value={chargerId} onValueChange={(v) => { setChargerId(v); clearError("chargerId", v); }}>
                <SelectTrigger {...fieldProps("chargerId")} data-testid="my-charger-select"><SelectValue placeholder="Choose a charger" /></SelectTrigger>
                <SelectContent>{myChargers.map((c) => <SelectItem key={c.charger_id} value={c.charger_id}>{c.charger_id} — {c.name}</SelectItem>)}</SelectContent>
              </Select>
              {fieldError("chargerId")}
              {selected && <dl className="rounded-xl border border-border p-5 grid grid-cols-1 sm:grid-cols-2 gap-3 text-base break-words" data-testid="selected-charger-info">
                <dt className="text-muted-foreground">Charger</dt><dd>{selected.name}</dd>
                <dt className="text-muted-foreground">Connector</dt><dd>{selected.connector}</dd>
                <dt className="text-muted-foreground">Power</dt><dd>{selected.max_power_kw} kW</dd>
                <dt className="text-muted-foreground">Location</dt><dd>{selected.location || "—"}</dd>
              </dl>}
            </>}
          </div> : <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {[['brand', 'Brand *', 'e.g. ABB, Delta, Tata Power'], ['model', 'Model *', 'e.g. Terra AC, AC Mini 7.4']].map(([key, label, example]) => <div className="space-y-2" key={key}>
              <Label htmlFor={key}>{label}</Label><Input {...fieldProps(key)} data-testid={`${key}-input`} value={info[key]} onChange={(e) => updateInfo(key, e.target.value)} placeholder={example} />{fieldError(key)}
            </div>)}
            <div className="space-y-2"><Label htmlFor="charger_type">Charger type *</Label>
              <Select value={info.charger_type} onValueChange={(v) => updateInfo("charger_type", v)}>
                <SelectTrigger {...fieldProps("charger_type", "type-help")} data-testid="type-select"><SelectValue placeholder="Choose a type" /></SelectTrigger>
                <SelectContent>{TYPE_OPTIONS.map((t) => <SelectItem key={t.value} value={t.value} className="text-base">{t.label}</SelectItem>)}</SelectContent>
              </Select><p id="type-help" className="text-sm text-muted-foreground">Don’t know the type? Choose “Not sure”.</p>{fieldError("charger_type")}
            </div>
            <div className="space-y-2"><Label htmlFor="serial_number">Serial number (optional)</Label><Input id="serial_number" aria-describedby="serial-help" data-testid="serial-input" value={info.serial_number} onChange={(e) => updateInfo("serial_number", e.target.value)} /><p id="serial-help" className="text-sm text-muted-foreground">Usually printed on the charger label</p></div>
            <div className="space-y-2"><Label htmlFor="power_rating">Power rating (optional)</Label><Input id="power_rating" data-testid="power-input" value={info.power_rating} onChange={(e) => updateInfo("power_rating", e.target.value)} placeholder="e.g. 7.4 kW" /></div>
            <div className="space-y-2"><Label htmlFor="purchase_date">Purchase date (optional)</Label><Input id="purchase_date" data-testid="purchase-input" type="date" value={info.purchase_date} onChange={(e) => updateInfo("purchase_date", e.target.value)} /></div>
          </div>}
        </section>
        <section className="repair-section" aria-labelledby="problem-heading">
          <h2 id="problem-heading">3. Tell us what’s wrong</h2>
          <p className="mb-6 text-base leading-relaxed text-muted-foreground">Choose the closest problem and describe what happens when you try to use the charger.</p>
          <div className="space-y-6">
            <div className="space-y-2"><Label htmlFor="category">Problem category (optional)</Label>
              <Select value={category} onValueChange={setCategory}><SelectTrigger id="category" data-testid="category-select"><SelectValue placeholder="Choose the closest problem" /></SelectTrigger>
                <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c} className="text-base">{c}</SelectItem>)}</SelectContent>
              </Select></div>
            <div className="space-y-2"><Label htmlFor="description">Describe the problem *</Label>
              <Textarea {...fieldProps("description", "description-help")} data-testid="description-input" value={description} onChange={(e) => { setDescription(e.target.value); clearError("description", e.target.value); }} rows={5} className="min-h-[140px]" />
              <p id="description-help" className="text-sm leading-relaxed text-muted-foreground">Include any error message, unusual sound, damaged cable, or what happens when charging starts.</p>{fieldError("description")}
            </div>
          </div>
        </section>
        <section className="repair-section" aria-labelledby="photos-heading">
          <h2 id="photos-heading">4. Add photos <span className="text-base font-normal text-muted-foreground">(optional)</span></h2>
          <p id="photo-help" className="text-base text-muted-foreground mb-2">Show the charger, label, connector, cable or visible damage.</p>
          <p id="photo-limits" className="text-sm text-muted-foreground mb-4">Up to 5 photos · 5 MB each</p>
          <div className="flex flex-wrap gap-4">
            {photos.map((p, i) => <div key={i} className="relative h-28 w-28 rounded-xl overflow-hidden border border-border" data-testid={`photo-${i}`}>
              <img src={p.data} alt={p.name} className="h-full w-full object-cover" />
              <button type="button" aria-label={`Remove photo ${i + 1}: ${p.name}`} onClick={() => setPhotos(photos.filter((_, idx) => idx !== i))} data-testid={`remove-photo-${i}`} className="absolute top-1 right-1 h-11 w-11 rounded-full bg-black/80 text-white flex items-center justify-center"><X className="h-5 w-5" aria-hidden="true" /></button>
            </div>)}
            {photos.length < MAX_PHOTOS && <label data-testid="photo-upload" className="relative min-h-[140px] w-full sm:w-64 rounded-xl border-2 border-dashed border-border flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-charging focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
              <Camera className="h-7 w-7 text-muted-foreground" aria-hidden="true" /><span className="text-base font-medium">Add photos</span>
              <input type="file" aria-label="Add photos" aria-describedby="photo-help photo-limits" accept="image/*" multiple className="absolute inset-0 opacity-0 w-full h-full cursor-pointer" onChange={onFiles} data-testid="photo-input" />
            </label>}
          </div>
        </section>
        <section className="repair-section" aria-labelledby="review-heading">
          <h2 id="review-heading">5. Review and submit</h2>
          <dl className="rounded-xl border border-border bg-secondary/20 p-5 sm:p-6 space-y-5 text-base break-words" data-testid="review-section">
            <div><dt className="text-sm font-medium text-muted-foreground mb-1">Charger</dt><dd>{source === "mine" ? (selected ? `${selected.charger_id} — ${selected.name}` : "No charger selected") : [info.brand, info.model, TYPE_OPTIONS.find((t) => t.value === info.charger_type)?.label].filter(Boolean).join(" · ") || "Charger details not added yet"}</dd>{source === "other" && info.serial_number && <dd className="mt-1 text-sm text-muted-foreground">Serial number: {info.serial_number}</dd>}</div>
            <div><dt className="text-sm font-medium text-muted-foreground mb-1">Problem</dt><dd>{category || "No category selected"}</dd></div>
            <div><dt className="text-sm font-medium text-muted-foreground mb-1">Description</dt><dd className="whitespace-pre-wrap">{description || "No description added yet"}</dd></div>
            <div><dt className="text-sm font-medium text-muted-foreground mb-1">Photos</dt><dd>{photos.length} attached</dd></div>
          </dl>
          <div className="mt-6 rounded-xl bg-charging/5 border border-charging/30 p-5 text-base leading-relaxed">
            <p className="font-semibold flex items-start gap-3"><ShieldCheck className="h-6 w-6 text-charging shrink-0" aria-hidden="true" />No payment is required to submit a repair request.</p>
            <p className="text-muted-foreground mt-3">After we receive and inspect your charger, we’ll share a repair estimate for your approval before work begins.</p>
          </div>
          <Button type="submit" disabled={submitting} aria-busy={submitting} data-testid="submit-repair-btn" className="w-full h-[52px] mt-6 rounded-lg text-base">
            {submitting ? <><Loader2 className="h-5 w-5 animate-spin mr-2" aria-hidden="true" />Submitting request…</> : <>Submit repair request <ArrowRight className="h-5 w-5 ml-2" aria-hidden="true" /></>}
          </Button>
        </section>
      </form>
    </div>
  </CustomerShell>;
}
