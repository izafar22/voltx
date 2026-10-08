import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { FEATURES } from "../config/features";
import { PRODUCT_NAME } from "../config/brand";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { homeFor } from "../components/ProtectedRoute";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

const normalizedPhone = (value) => {
  if (!/^\+?[\d\s()-]+$/.test(value.trim())) return null;
  let digits = value.replace(/[\s()+-]/g, "");
  if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
  return /^[6-9]\d{9}$/.test(digits) ? `+91${digits}` : null;
};
function authMessage(error, fallback) {
  const status = error.response?.status;
  if (status === 429) return "Too many requests or attempts. Wait before resending a new code.";
  if (status === 401) return "Your verification expired. Change phone number to start again.";
  if (status === 403) return "This account is unavailable. Contact support.";
  if (status === 409) return "An account already exists. Please sign in again.";
  if (status === 503) return "Code delivery is unavailable. Please try again later.";
  if (status === 400) return "Incorrect, expired, or already used code. Try again or request a new code.";
  return fallback;
}
export default function Login() {
  const demoEnabled = process.env.NODE_ENV !== "production" && process.env.REACT_APP_DEMO_AUTH === "true";
  const navigate = useNavigate();
  const { user, loading: checking, login, authError, loadMe } = useAuth();
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [challenge, setChallenge] = useState(null);
  const [registrationToken, setRegistrationToken] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [remaining, setRemaining] = useState(0);
  const resendAt = useRef(0);
  const lock = useRef(false);
  useEffect(() => {
    if (step !== "otp") return;
    const tick = () => setRemaining(Math.max(0, Math.ceil((resendAt.current - Date.now()) / 1000)));
    tick(); const timer = setInterval(tick, 1000); return () => clearInterval(timer);
  }, [step, challenge]);
  const run = async (action, fallback) => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try { await action(); }
    catch (e) {
      const retry = Number(e.response?.headers?.["retry-after"]);
      if (e.response?.status === 429 && retry > 0) { resendAt.current = Date.now() + retry * 1000; setRemaining(retry); }
      setError(authMessage(e, fallback));
    } finally { lock.current = false; setBusy(false); }
  };
  const requestCode = (value = phone) => {
    const normalized = normalizedPhone(value);
    if (!normalized) { setError("Enter a valid 10-digit Indian mobile number."); return; }
    run(async () => {
      const { data } = await api.post("/auth/request-otp", { phone: normalized });
      setPhone(normalized); setOtp(""); setChallenge(data);
      resendAt.current = Date.now() + data.resend_after * 1000;
      setRemaining(data.resend_after); setStep("otp");
    }, "Unable to request a code. Please try again.");
  };
  const complete = (data) => { login(data.user); navigate(homeFor(data.user.role), { replace: true }); };
  const verify = (event) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(otp)) { setError("Enter the six-digit code."); return; }
    run(async () => {
      const { data } = await api.post("/auth/verify-otp", { phone, challenge_id: challenge.challenge_id, otp });
      if (data.registration_required) { setRegistrationToken(data.registration_token); setStep("register"); setOtp(""); setChallenge(null); }
      else complete(data);
    }, "Unable to verify the code. Please try again.");
  };
  const register = (event) => {
    event.preventDefault();
    if (name.trim().length < 2 || name.trim().length > 100) { setError("Enter your full name (2–100 characters)."); return; }
    if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { setError("Enter a valid email address."); return; }
    run(async () => {
      const { data } = await api.post("/auth/register-customer", { name: name.trim(), email: email.trim() }, { headers: { Authorization: `Bearer ${registrationToken}` } });
      setRegistrationToken(null); complete(data);
    }, "Unable to create your account. Please try again.");
  };
  const changePhone = () => { setStep("phone"); setChallenge(null); setRegistrationToken(null); setOtp(""); setError(""); };
  if (checking) return <p role="status" className="p-8">Checking your session…</p>;
  if (user) return <Navigate to={homeFor(user.role)} replace />;
  return <div className="min-h-screen grid lg:grid-cols-2">
    <div className="hidden lg:flex flex-col justify-between bg-primary text-primary-foreground p-12">
      <Logo />{FEATURES.repair && !FEATURES.charging ? <div><h2 className="font-display text-5xl font-light leading-tight">Get your charger<br /><span className="text-charging font-medium">working again.</span></h2><p className="mt-5 opacity-70 max-w-sm">Repair AC, DC or portable chargers of any brand. Request a repair and track its progress with Voltx.</p></div> : <div><h2 className="font-display text-5xl font-light leading-tight">Charge<br />as fast as<br /><span className="text-charging font-medium">you pay.</span></h2><p className="mt-5 opacity-70 max-w-sm">Find your next charge. Navigate, connect, and manage your charging across India.</p></div>}<p className="text-sm opacity-60">{PRODUCT_NAME} {FEATURES.repair && !FEATURES.charging ? "Charger Repair" : "Network"}</p>
    </div>
    <div className="flex items-center justify-center p-6"><div className="w-full max-w-sm space-y-6">
      <div className="lg:hidden"><Logo /></div>
      {authError && <div role="alert"><p>{authError}</p><button onClick={loadMe} className="underline">Retry session check</button></div>}
      {error && <p id="auth-error" role="alert" className="text-sm text-destructive">{error}</p>}
      {step === "phone" && <form onSubmit={(event) => { event.preventDefault(); requestCode(); }} className="space-y-5" data-testid="phone-step">
        <div><h1 className="font-display text-3xl font-medium">Sign in</h1><p className="mt-2 text-muted-foreground">Enter your phone number to continue.</p></div>
        <div><label htmlFor="phone">Phone number</label><Input id="phone" type="tel" autoComplete="tel" inputMode="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="98765 43210" maxLength={40} disabled={busy} aria-describedby={error ? "auth-error" : undefined} data-testid="phone-input" className="h-12 mt-2" /></div>
        <Button type="submit" disabled={busy || !phone.trim()} className="w-full h-12" data-testid="send-otp-btn">{busy ? "Requesting code…" : "Send OTP"}</Button>
        {demoEnabled && <div><p className="text-xs text-muted-foreground mb-2">Development demo accounts</p><div className="flex gap-2">{[["Admin", "+919000000001"], ["Owner", "+919000000002"], ["Customer", "+919000000003"]].map(([label, number]) => <Button key={label} type="button" variant="outline" disabled={busy} onClick={() => requestCode(number)}>{label}</Button>)}</div></div>}
      </form>}
      {step === "otp" && <form onSubmit={verify} className="space-y-5" data-testid="otp-step">
        <div><h1 className="font-display text-3xl font-medium">Enter code</h1><p className="mt-2 text-muted-foreground">Code sent to +91••••••{phone.slice(-4)}</p></div>
        {demoEnabled && challenge?.demo_otp && <p>Demo code: {challenge.demo_otp}</p>}
        <div><label htmlFor="otp">Six-digit code</label><Input id="otp" autoComplete="one-time-code" inputMode="numeric" maxLength={6} value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))} disabled={busy} aria-describedby={error ? "auth-error" : undefined} data-testid="otp-input" className="h-14 text-center text-2xl font-mono tracking-widest" /></div>
        <Button type="submit" disabled={busy || otp.length !== 6} className="w-full h-12" data-testid="verify-otp-btn">{busy ? "Verifying…" : "Verify"}</Button>
        <p className="text-xs text-muted-foreground">Codes expire after 5 minutes.</p>
        <Button type="button" variant="outline" disabled={busy || remaining > 0} onClick={() => requestCode()} className="w-full">{remaining > 0 ? `Resend in ${remaining}s` : "Resend code"}</Button>
      </form>}
      {step === "register" && <form onSubmit={register} className="space-y-5" data-testid="registration-step" noValidate>
        <div><h1 className="font-display text-3xl font-medium">Create your account</h1><p className="mt-2 text-muted-foreground">Your number has been verified.</p></div>
        <div><label htmlFor="full-name">Full name *</label><Input id="full-name" autoComplete="name" value={name} maxLength={100} onChange={e => setName(e.target.value)} disabled={busy} className="h-12 mt-2" /></div>
        <div><label htmlFor="email">Email (optional)</label><Input id="email" type="email" autoComplete="email" value={email} maxLength={254} onChange={e => setEmail(e.target.value)} disabled={busy} className="h-12 mt-2" /></div>
        <Button type="submit" disabled={busy} className="w-full h-12">{busy ? "Creating account…" : "Create account"}</Button>
      </form>}
      {step !== "phone" && <button type="button" onClick={changePhone} disabled={busy} className="text-sm underline focus-visible:outline focus-visible:outline-2" data-testid="change-phone-btn">Change phone number</button>}
    </div></div>
  </div>;
}
