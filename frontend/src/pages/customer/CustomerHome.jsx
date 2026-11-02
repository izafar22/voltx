import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { QrCode, Plus, Zap, ArrowRight, Navigation, Wrench } from "lucide-react";
import { api, inr } from "../../lib/api";
import { getStatusGroup } from "../../lib/stationStatus";
import { useAuth } from "../../context/AuthContext";
import { CustomerShell } from "../../components/layout/CustomerShell";
import { StationsMap } from "../../components/StationsMap";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { FEATURES } from "../../config/features";
import { RepairOverview } from "../../components/RepairOverview";
import "./CustomerHome.css";

const EMPTY = [];
const money = (value) => typeof value === "number" && Number.isFinite(value) ? inr(value) : "—";
const energy = (value) => typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(2)} kWh` : "—";
const dateTime = (value) => value && Number.isFinite(new Date(value).getTime()) ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "Date unavailable";
function Skeleton({ label }) { return <div className="dashboard-skeleton" role="status" aria-label={label}><span className="sr-only">{label}</span></div>; }
function Failure({ children, retry }) { return <div className="dashboard-error" role="alert"><p>{children}</p><Button variant="outline" size="sm" onClick={retry}>Retry</Button></div>; }

export default function CustomerHome() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [resolving, setResolving] = useState(false);
  const resolveLock = useRef(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [nearbyCount, setNearbyCount] = useState(null);
  const showMap = FEATURES.charging && FEATURES.stationDiscovery && FEATURES.stationMap;
  const showStations = FEATURES.charging && FEATURES.stationDiscovery;
  const showSupport = FEATURES.wallet || FEATURES.charging;
  const walletQuery = useQuery({ queryKey: ["wallet"], enabled: FEATURES.wallet, queryFn: async () => (await api.get("/wallet")).data });
  const sessionQuery = useQuery({ queryKey: ["sessions"], enabled: FEATURES.charging, queryFn: async () => (await api.get("/sessions")).data });
  const stationQuery = useQuery({ queryKey: ["stations"], enabled: showStations, queryFn: async () => (await api.get("/stations")).data });
  const sessions = sessionQuery.data || EMPTY;
  const stations = stationQuery.data || EMPTY;
  const active = sessions.find((s) => s.status === "active");
  const counts = useMemo(() => stations.reduce((result, station) => {
    result[getStatusGroup(station.status)] += 1; return result;
  }, { available: 0, "in-use": 0, fault: 0, offline: 0 }), [stations]);

  const goCharger = async (event) => {
    event?.preventDefault();
    if (resolveLock.current) return;
    const cid = code.trim().toUpperCase();
    if (!cid) { setCodeError("Enter a station code."); return; }
    resolveLock.current = true; setResolving(true); setCodeError("");
    try {
      await api.get(`/chargers/${encodeURIComponent(cid)}`);
      setScanOpen(false); navigate(`/app/charger/${encodeURIComponent(cid)}`);
    } catch (error) {
      setCodeError(error.response?.status === 404 ? "Station code not found. Check the code on the charger." : "Unable to look up this station. Please try again.");
    } finally { resolveLock.current = false; setResolving(false); }
  };
  const codeForm = (scan = false) => <form onSubmit={goCharger} className="space-y-2">
    <label className="sr-only" htmlFor={scan ? "scan-code" : "station-code"}>Station code</label>
    <div className="flex gap-2">
      <Input id={scan ? "scan-code" : "station-code"} data-testid={scan ? "scan-code-input" : "station-code-input"} value={code} onChange={(e) => { setCode(e.target.value); setCodeError(""); }} placeholder="Station ID" className="h-11 min-w-0 font-mono" disabled={resolving} aria-invalid={!!codeError} aria-describedby={codeError ? (scan ? "scan-error" : "code-error") : undefined} />
      <Button type="submit" disabled={!code.trim() || resolving} data-testid={scan ? "scan-go-btn" : "code-go-btn"} aria-label="Look up station" className="h-11 shrink-0">{resolving ? "Looking up…" : <ArrowRight aria-hidden="true" className="h-4 w-4" />}</Button>
    </div>
    {codeError && <p id={scan ? "scan-error" : "code-error"} role="alert" className="text-sm text-destructive">{codeError}</p>}
  </form>;

  return <CustomerShell><div className="customer-dashboard">
    <div><p className="text-sm text-muted-foreground">Welcome back</p><h1 className="font-display text-2xl lg:text-3xl font-semibold tracking-tight break-words">{user?.name || "Your repair dashboard"}</h1></div>
    {FEATURES.charging && active && <button onClick={() => navigate(`/app/live/${active.session_id}`)} data-testid="active-session-banner" className="dashboard-active"><span><strong>Charging in progress</strong><span className="block text-sm">{active.charger_name}</span></span><ArrowRight aria-hidden="true" className="h-5 w-5" /></button>}
    {FEATURES.repair && <>
      <section className="dashboard-repair-hero dashboard-card" aria-labelledby="repair-title">
        <div><p className="text-sm text-muted-foreground mb-2">Charger repair, any brand</p><h2 id="repair-title" className="font-display text-2xl font-semibold">Get your charger working again</h2><p className="text-sm text-muted-foreground mt-3">Request a repair for your AC, DC or portable charger and track its progress with RushX.</p></div>
        <Button data-testid="repair-charger-btn" onClick={() => navigate("/repairs/new")} className="dashboard-repair-cta"><Wrench aria-hidden="true" className="h-5 w-5 mr-2 shrink-0" />Repair a Charger<ArrowRight aria-hidden="true" className="h-4 w-4 ml-2 shrink-0" /></Button>
      </section>
      <RepairOverview />
    </>}
    {(showMap || showSupport) && <div className={`dashboard-grid${showMap ? " dashboard-grid-with-map" : ""}`}>

      {showMap && <section className="dashboard-map dashboard-card" aria-labelledby="map-title">
        <div className="dashboard-map-header"><div className="flex items-center gap-2"><Navigation aria-hidden="true" className="h-5 w-5 shrink-0 text-charging" /><h2 id="map-title" className="font-display font-semibold">Nearby charging stations</h2></div>
          {stationQuery.isPending ? <Skeleton label="Loading station summary" /> : !stationQuery.isError && <p className="text-xs text-muted-foreground" title={nearbyCount !== null ? "Within 10 km, straight-line distance" : "Available in the loaded station dataset"}>{nearbyCount !== null ? `${nearbyCount} available within 10 km` : `${counts.available} available in loaded stations`}</p>}
        </div>
        <div className="dashboard-map-body">
          <StationsMap stations={stations} onNearbyCount={setNearbyCount} />
          {stationQuery.isPending && <div className="dashboard-map-message"><Skeleton label="Loading charging stations" /></div>}
          {stationQuery.isError && <div className="dashboard-map-message"><Failure retry={stationQuery.refetch}>Unable to load charging stations</Failure></div>}
          {!stationQuery.isPending && !stationQuery.isError && stations.length === 0 && <div className="dashboard-map-message">No charging stations found. Try again later.</div>}
        </div>
      </section>}
      {showSupport && <div className="dashboard-support">
        {FEATURES.wallet && <section className="dashboard-wallet" data-testid="wallet-card" aria-label="Wallet">
          <p className="text-xs uppercase tracking-widest opacity-80">Wallet balance</p>
          {walletQuery.isPending ? <Skeleton label="Loading wallet" /> : walletQuery.isError ? <Failure retry={walletQuery.refetch}>Unable to load wallet balance</Failure> : <p className="font-mono text-4xl font-light mt-2" data-testid="wallet-balance">{money(walletQuery.data?.balance)}</p>}
          <Button onClick={() => navigate("/app/wallet")} data-testid="add-money-btn" size="sm" className="mt-4 bg-charging text-black hover:bg-charging/90"><Plus aria-hidden="true" className="h-4 w-4 mr-1" />Add money</Button>
        </section>}
        {FEATURES.charging && FEATURES.qrCharging && <Dialog open={scanOpen} onOpenChange={setScanOpen}>
          <DialogTrigger asChild><button data-testid="scan-qr-btn" className="dashboard-action"><QrCode aria-hidden="true" className="h-6 w-6 text-charging shrink-0" /><span><strong>Scan QR</strong><span>Scan a charger or enter its code</span></span><ArrowRight aria-hidden="true" className="h-4 w-4 ml-auto shrink-0" /></button></DialogTrigger>
          <DialogContent data-testid="scan-dialog"><DialogHeader><DialogTitle>Scan charger QR</DialogTitle><DialogDescription>Camera scanning is not available here yet. Enter the station code printed on the charger to continue.</DialogDescription></DialogHeader>{codeForm(true)}</DialogContent>
        </Dialog>}
        {FEATURES.charging && <section className="dashboard-card p-4"><h2 className="font-semibold flex items-center gap-2 mb-3"><Zap aria-hidden="true" className="h-5 w-5 text-charging" />Enter station code</h2>{codeForm()}</section>}
        {showStations && <section className="dashboard-card p-4" aria-label="Station status summary"><h2 className="text-xs uppercase tracking-widest text-muted-foreground mb-3">Loaded station status</h2>
          {stationQuery.isPending ? <Skeleton label="Loading station counts" /> : stationQuery.isError ? <p className="text-sm text-muted-foreground">Station counts unavailable</p> : <dl className="grid grid-cols-4 gap-2 text-center">{[["Available", counts.available], ["In use", counts["in-use"]], ["Unavailable", counts.fault + counts.offline], ["Total", stations.length]].map(([label, count]) => <div key={label}><dd className="font-mono text-xl">{count}</dd><dt className="text-[10px] text-muted-foreground">{label}</dt></div>)}</dl>}
        </section>}
      </div>}
    </div>}
    {FEATURES.charging && <section aria-labelledby="recent-title"><h2 id="recent-title" className="font-display text-lg font-semibold mb-3">Recent charging</h2>
      {sessionQuery.isPending ? <Skeleton label="Loading recent charging" /> : sessionQuery.isError ? <Failure retry={sessionQuery.refetch}>Unable to load recent charging</Failure> : sessions.length === 0 ? <div className="dashboard-card p-5"><p>No charging sessions yet</p><p className="text-sm text-muted-foreground mt-1">Choose a station on the map to plan your first charge.</p></div> : <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-testid="recent-sessions">{sessions.slice(0, 6).map((s) => <article key={s.session_id} className="dashboard-card p-4 min-w-0"><div className="flex justify-between gap-3"><h3 className="font-semibold text-sm break-words">{s.charger_name || "Charging station"}</h3><span className="text-xs capitalize">{s.status === "active" ? "Active" : s.status || "Completed"}</span></div><p className="text-xs text-muted-foreground mt-1">{dateTime(s.start_time)}</p><div className="flex justify-between mt-3 font-mono text-sm"><span>{money(s.cost)}</span><span>{energy(s.energy_kwh)}</span></div></article>)}</div>}
    </section>}
  </div></CustomerShell>;
}
