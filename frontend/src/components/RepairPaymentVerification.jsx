import { useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export default function RepairPaymentVerification({ repair, onSaved }) {
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const save = async (event) => {
    event.preventDefault();
    if (busy) return;
    const value = Number(amount);
    if (!amount.trim() || !Number.isFinite(value) || value < 0 || value > 99999999.99 || reference.trim().length < 3) {
      setMessage("Enter a valid outstanding amount and reconciliation reference.");
      return;
    }
    setBusy(true); setMessage("");
    try {
      await api.patch(`/repairs/${repair.id}/payment`, { amount_due: value, reference: reference.trim() });
      setMessage("Outstanding amount verified. Update the repair status when ready.");
      onSaved();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setMessage(typeof detail === "string" ? detail : "Could not save the verified amount. Please try again.");
    } finally { setBusy(false); }
  };
  return <section className="rounded-xl border border-border p-5" aria-labelledby="verify-balance-heading">
    <h3 id="verify-balance-heading" className="font-semibold">Verify outstanding payment</h3>
    <p className="mt-2 text-sm text-muted-foreground">Reconcile all confirmed payments before entering the remaining balance. Saving this record does not collect money or send a payment message.</p>
    <form onSubmit={save} noValidate className="mt-4 space-y-3">
      <Label htmlFor="verified-due">Outstanding amount (INR)</Label>
      <Input id="verified-due" type="number" min="0" max="99999999.99" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} />
      <Label htmlFor="payment-reference">Reconciliation reference (internal)</Label>
      <Input id="payment-reference" maxLength={120} value={reference} onChange={e => setReference(e.target.value)} />
      <Button type="submit" disabled={busy}>{busy ? "Saving…" : "Save verified amount"}</Button>
      {message && <p role="status" className="text-sm">{message}</p>}
    </form>
  </section>;
}
