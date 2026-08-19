import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { ArrowRight, Loader2, Smartphone, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { homeFor } from "@/components/ProtectedRoute";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const demoAccounts = [
  { label: "Admin", phone: "+919000000001" },
  { label: "Owner", phone: "+919000000002" },
  { label: "Customer", phone: "+919000000003" },
];

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [otp, setOtp] = useState("");
  const [demoCode, setDemoCode] = useState("");
  const [loading, setLoading] = useState(false);

  const sendOtp = async (p = phone) => {
    if (!p || p.length < 10) { toast.error("Enter a valid phone number"); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/auth/request-otp", { phone: p });
      setDemoCode(data.demo_otp);
      setStep("otp");
      toast.success("OTP sent", { description: data.message });
    } catch { toast.error("Could not send OTP"); }
    finally { setLoading(false); }
  };

  const verify = async () => {
    if (otp.length !== 6) { toast.error("Enter the 6-digit OTP"); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/auth/verify-otp", { phone, otp, name: name || undefined });
      login(data.token, data.user);
      toast.success(`Welcome, ${data.user.name}`);
      navigate(homeFor(data.user.role));
    } catch (e) {
      toast.error(e.response?.data?.detail || "Verification failed");
    } finally { setLoading(false); }
  };

  const quick = (p) => { setPhone(p); sendOtp(p); };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-primary text-primary-foreground p-12 relative overflow-hidden">
        <div className="absolute inset-0 grain opacity-40" />
        <div className="relative"><Logo /></div>
        <div className="relative">
          <h2 className="font-display text-5xl font-light tracking-tighter leading-[1.05]">Charge<br />as fast as<br /><span className="text-charging font-medium">you pay.</span></h2>
          <p className="mt-5 text-primary-foreground/70 max-w-sm">Scan, start, and go. Wallet-based billing with instant, frictionless EV charging across India.</p>
        </div>
        <div className="relative text-sm text-primary-foreground/50">VoltGrid Network · Powered by OCPP 1.6J</div>
      </div>

      <div className="flex items-center justify-center p-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
          <div className="lg:hidden mb-8"><Logo /></div>
          {step === "phone" ? (
            <div data-testid="phone-step">
              <div className="h-11 w-11 rounded-xl bg-charging/10 flex items-center justify-center mb-5"><Smartphone className="h-5 w-5 text-charging" /></div>
              <h1 className="font-display text-3xl font-medium tracking-tight">Sign in</h1>
              <p className="mt-2 text-muted-foreground">We'll send a one-time code to your phone.</p>
              <div className="mt-7 space-y-4">
                <div className="space-y-1.5"><Label>Phone number</Label><Input data-testid="phone-input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 90000 00000" className="h-12 font-mono" /></div>
                <div className="space-y-1.5"><Label>Name <span className="text-muted-foreground">(new users)</span></Label><Input data-testid="name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" className="h-12" /></div>
                <Button onClick={() => sendOtp()} disabled={loading} data-testid="send-otp-btn" className="w-full h-12 rounded-lg text-base active:scale-95 transition-transform duration-200">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Send OTP <ArrowRight className="h-4 w-4 ml-2" /></>}
                </Button>
              </div>
              <div className="mt-8">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Demo accounts (OTP 123456)</p>
                <div className="grid grid-cols-3 gap-2">
                  {demoAccounts.map((d) => (
                    <button key={d.phone} onClick={() => quick(d.phone)} data-testid={`demo-${d.label.toLowerCase()}`} className="rounded-lg border border-border/60 px-2 py-2 text-sm hover:bg-secondary transition-colors duration-200">{d.label}</button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div data-testid="otp-step">
              <div className="h-11 w-11 rounded-xl bg-charging/10 flex items-center justify-center mb-5"><ShieldCheck className="h-5 w-5 text-charging" /></div>
              <h1 className="font-display text-3xl font-medium tracking-tight">Enter code</h1>
              <p className="mt-2 text-muted-foreground">Sent to <span className="font-mono text-foreground">{phone}</span></p>
              {demoCode && <div className="mt-4 rounded-lg bg-charging/10 border border-charging/30 px-4 py-2 text-sm">Demo code: <span className="font-mono font-semibold text-charging">{demoCode}</span></div>}
              <div className="mt-6 space-y-4">
                <Input data-testid="otp-input" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="••••••" maxLength={6} className="h-14 text-center text-2xl font-mono tracking-[0.5em]" />
                <Button onClick={verify} disabled={loading} data-testid="verify-otp-btn" className="w-full h-12 rounded-lg text-base active:scale-95 transition-transform duration-200">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Verify & continue"}
                </Button>
                <button onClick={() => { setStep("phone"); setOtp(""); }} data-testid="change-phone-btn" className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors duration-200">Change number</button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
