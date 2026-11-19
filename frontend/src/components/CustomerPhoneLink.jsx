import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { profileError } from "../lib/customerProfile";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";

export function CustomerPhoneLink({ hasPhone, onSaved, onClose, onBeginSave }) {
  const [phone, setPhone] = useState(""),
    [otp, setOtp] = useState(""),
    [challenge, setChallenge] = useState(null);
  const [remaining, setRemaining] = useState(0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const lock = useRef(false);
  useEffect(() => {
    if (!remaining) return;
    const timer = setTimeout(
      () => setRemaining((n) => Math.max(0, n - 1)),
      1000,
    );
    return () => clearTimeout(timer);
  }, [remaining]);
  const execute = async (verify) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    const complete = verify ? onBeginSave?.() : undefined;
    try {
      if (verify) {
        const { data } = await api.post("/auth/link/phone/verify", {
          phone,
          otp,
          challenge_id: challenge.challenge_id,
        });
        await onSaved(data.user, complete);
      } else {
        const { data } = await api.post("/auth/link/phone/request", { phone });
        setChallenge(data);
        setOtp("");
        setRemaining(data.resend_after);
      }
    } catch (e) {
      setError(profileError(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {hasPhone ? "Change mobile number" : "Add mobile number"}
          </DialogTitle>
          <DialogDescription>
            Verify this number through WhatsApp. You can then use it for repair
            contact and sign-in.
            {hasPhone &&
              " Your current number stays active until verification succeeds. Other sessions will be signed out after the change."}
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            execute(!!challenge);
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="link-phone">Mobile number</Label>
            <Input
              id="link-phone"
              type="tel"
              autoComplete="tel"
              maxLength={40}
              required
              value={phone}
              disabled={!!challenge || busy}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          {challenge && (
            <div className="space-y-2">
              <Label htmlFor="link-otp">WhatsApp verification code</Label>
              <Input
                key={challenge.challenge_id}
                autoFocus
                id="link-otp"
                autoComplete="one-time-code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Enter the six-digit code sent to your number.
              </p>
            </div>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={busy}>
              {busy
                ? "Please wait…"
                : challenge
                  ? "Verify and connect"
                  : "Send WhatsApp code"}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={onClose}
            >
              Cancel
            </Button>
          </div>
          {challenge && (
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                variant="ghost"
                disabled={busy || remaining > 0}
                onClick={() => execute(false)}
              >
                {remaining ? `Resend in ${remaining}s` : "Resend code"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={busy}
                onClick={() => {
                  setChallenge(null);
                  setOtp("");
                  setError("");
                }}
              >
                Change number
              </Button>
            </div>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
