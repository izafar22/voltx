import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Plus, ArrowUpRight, ArrowDownLeft, Loader2, Wallet as WalletIcon } from "lucide-react";
import { api, inr, inr0 } from "@/lib/api";
import { CustomerShell } from "@/components/layout/CustomerShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const quickAmounts = [200, 500, 1000, 2000];

export default function WalletPage() {
  const qc = useQueryClient();
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);

  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: async () => (await api.get("/wallet")).data });
  const { data: txns = [] } = useQuery({ queryKey: ["wtxns"], queryFn: async () => (await api.get("/wallet/transactions")).data });

  const topup = async (amt) => {
    const value = Number(amt || amount);
    if (!value || value <= 0) { toast.error("Enter an amount"); return; }
    setLoading(true);
    try {
      await api.post("/wallet/topup", { amount: value });
      toast.success(`${inr0(value)} added to wallet`);
      setAmount("");
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["wtxns"] });
    } catch { toast.error("Top-up failed"); }
    finally { setLoading(false); }
  };

  return (
    <CustomerShell>
      <div className="p-5 space-y-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl bg-primary text-primary-foreground p-6 relative overflow-hidden" data-testid="wallet-balance-card">
          <div className="absolute inset-0 grain opacity-30" />
          <div className="relative">
            <p className="text-xs uppercase tracking-[0.2em] text-primary-foreground/60">Available balance</p>
            <p className="font-mono text-5xl font-light tabular mt-1" data-testid="wallet-balance">{inr0(wallet?.balance)}</p>
          </div>
        </motion.div>

        <div>
          <h2 className="font-display text-lg font-semibold mb-3">Add money <span className="text-xs font-normal text-muted-foreground">(demo — no gateway)</span></h2>
          <div className="grid grid-cols-4 gap-2 mb-3">
            {quickAmounts.map((a) => (
              <button key={a} onClick={() => topup(a)} data-testid={`quick-${a}`} className="rounded-lg border border-border/60 py-2.5 text-sm font-medium hover:border-charging hover:text-charging transition-colors duration-200 active:scale-95">+{a}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <Input data-testid="topup-input" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Custom amount" className="h-12 font-mono" />
            <Button onClick={() => topup()} disabled={loading} data-testid="topup-btn" className="h-12 rounded-lg bg-charging text-black hover:bg-charging/90 active:scale-95 transition-transform duration-200">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Plus className="h-4 w-4 mr-1" /> Add</>}
            </Button>
          </div>
        </div>

        <div>
          <h2 className="font-display text-lg font-semibold mb-3">Transactions</h2>
          {txns.length === 0 ? <p className="text-sm text-muted-foreground flex items-center gap-2"><WalletIcon className="h-4 w-4" /> No transactions yet.</p> : (
            <div className="space-y-2" data-testid="wallet-transactions">
              {txns.map((t) => {
                const credit = t.amount >= 0;
                return (
                  <div key={t.id} className="flex items-center justify-between rounded-xl border border-border/60 p-4">
                    <div className="flex items-center gap-3">
                      <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${credit ? "bg-charging/15" : "bg-secondary"}`}>
                        {credit ? <ArrowDownLeft className="h-4.5 w-4.5 text-charging" /> : <ArrowUpRight className="h-4.5 w-4.5 text-muted-foreground" />}
                      </div>
                      <div><p className="text-sm font-medium capitalize">{t.note || t.type}</p><p className="text-xs text-muted-foreground">{new Date(t.created_at).toLocaleString("en-IN")}</p></div>
                    </div>
                    <div className="text-right">
                      <p className={`font-mono font-medium ${credit ? "text-charging" : ""}`}>{credit ? "+" : ""}{inr(t.amount)}</p>
                      <p className="text-xs text-muted-foreground font-mono">{inr0(t.balance_after)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </CustomerShell>
  );
}
