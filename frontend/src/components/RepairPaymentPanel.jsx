import { useEffect, useRef, useState } from "react";
import { api, inr } from "../lib/api";

const labels = { UNVERIFIED: "Balance awaiting review", PENDING: "Awaiting payment", AWAITING_MANUAL_VERIFICATION: "Reference submitted — awaiting verification", PAID: "Payment received and verified", BALANCE_CLEARED: "No outstanding balance" };

export default function RepairPaymentPanel({ repairId, admin = false, refreshToken, repairStatus }) {
  const [payment, setPayment] = useState(null);
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("upi");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const retry = useRef(null);
  const load = () => api.get(`/repairs/${repairId}/payment`).then(r => setPayment(r.data));
  useEffect(() => {
    let active = true;
    api.get(`/repairs/${repairId}/payment`).then(r => { if (active) setPayment(r.data); })
      .catch(() => { if (active) setMessage("Could not load payment details. Refresh to retry."); });
    return () => { active = false; };
  }, [repairId, refreshToken]);
  const submit = async event => {
    event.preventDefault();
    if (busy) return;
    const value = Number(amount);
    if (admin && (!confirmed || !amount.trim() || !Number.isFinite(value) || value <= 0 || value !== Number(payment.amount_due))) {
      setMessage("Confirm receipt of the exact outstanding amount in the merchant account."); return;
    }
    if ((!admin || method !== "cash") && reference.trim().length < (admin ? 6 : 3)) {
      setMessage("Enter a valid transaction reference."); return;
    }
    const body = admin ? { amount: value, method, reference: method === "cash" ? null : reference.trim(), funds_received: true } : { reference: reference.trim() };
    if (admin) {
      const fingerprint = JSON.stringify(body);
      if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
      body.idempotency_key = retry.current.key;
    }
    setBusy(true); setMessage("");
    try {
      await api.post(`/repairs/${repairId}/payment/${admin ? "verify" : "reference"}`, body);
      setMessage(admin ? "Payment verified. Any eligible WhatsApp acknowledgement is queued." : "Reference submitted for review. Payment has not been confirmed.");
      await load();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setMessage(typeof detail === "string" ? detail : "Could not save or refresh payment details. Retry with the same details.");
    } finally { setBusy(false); }
  };
  const payable = payment && Number(payment.amount_due) > 0 && payment.state !== "PAID";
  return <section className="mt-4 rounded-xl border border-border p-5" aria-label="RushX payment">
    <h3 className="font-semibold">RushX payment</h3>
    {payment && <>
      <p className="mt-2">{labels[payment.state] || "Awaiting review"}</p>
      {payment.amount_due != null && <p>Outstanding amount: {inr(payment.amount_due)}</p>}
      {payment.receipt?.verified_amount && <p>Received: {inr(payment.receipt.verified_amount)} · {payment.receipt.safe_reference}</p>}
      {payable && <>
        <p className="mt-2 text-sm">{payment.instructions}</p>
        {payment.qr_image_url && <img className="mt-3 h-56 w-56 object-contain" src={payment.qr_image_url} alt="RushX merchant UPI payment QR code" referrerPolicy="no-referrer" />}
        {admin && payment.evidence?.map((item, i) => <p key={i} className="mt-2 text-sm">Unverified customer reference: {item.reference}</p>)}
        {admin && repairStatus === "REPAIR_COMPLETED" ? <p>Set the repair status to payment pending before recording receipt.</p> : <form onSubmit={submit} noValidate className="mt-4 space-y-3">
          {admin && <>
            <label className="block">Amount received (INR)<input aria-label="Amount received (INR)" type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} className="block border rounded p-2 bg-background" /></label>
            <label className="block">Payment method<select aria-label="Payment method" value={method} onChange={e => setMethod(e.target.value)} className="block border rounded p-2 bg-background"><option value="upi">UPI</option><option value="bank_transfer">Bank transfer</option><option value="cash">Cash</option></select></label>
          </>}
          {(!admin || method !== "cash") && <label className="block">Transaction reference / UTR<input aria-label="Transaction reference / UTR" maxLength={120} value={reference} onChange={e => setReference(e.target.value)} className="block border rounded p-2 bg-background" /></label>}
          {admin ? <label className="block"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> I have confirmed funds actually reached the merchant account (or received the cash).</label> : <p className="text-sm">Submitting a reference is optional and does not confirm payment. RushX will verify receipt.</p>}
          <button className="rounded bg-primary text-primary-foreground px-4 py-2" disabled={busy} type="submit">{busy ? "Saving…" : admin ? "Verify payment received" : "Submit reference for review"}</button>
        </form>}
      </>}
    </>}
    {message && <p className="mt-2 text-sm" role="status">{message}</p>}
  </section>;
}
