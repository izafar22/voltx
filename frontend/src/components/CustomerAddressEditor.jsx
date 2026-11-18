import { useRef, useState } from "react";
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

export function CustomerAddressEditor({
  profile,
  address,
  onSaved,
  onClose,
  onStale,
  onBeginSave,
}) {
  const [form, setForm] = useState(() => ({
    label: "",
    line1: "",
    line2: "",
    city: "",
    state: "",
    pin: "",
    country: "India",
    ...address,
    default_pickup: address
      ? profile.pickup_id === address.id
      : profile.addresses.length === 0,
    default_delivery: address
      ? profile.delivery_id === address.id
      : profile.addresses.length === 0,
  }));
  const [baseRevision] = useState(() => profile.revision);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const lock = useRef(false);
  const save = async (event) => {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    const complete = onBeginSave?.();
    try {
      const { id, ...fields } = form;
      const { data } = await api[address ? "patch" : "post"](
        address ? `/customer/addresses/${address.id}` : "/customer/addresses",
        { ...fields, revision: baseRevision },
      );
      await onSaved(data, complete);
    } catch (e) {
      setError(profileError(e));
      if (e.response?.status === 409) {
        setError(
          "This address list changed. Close and reopen this form to review the latest details before saving.",
        );
        onStale?.();
      }
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
      <DialogContent className="max-h-screen overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{address ? "Edit address" : "Add address"}</DialogTitle>
          <DialogDescription>
            Save an address for pickup or delivery.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          {[
            ["label", "Label", 40],
            ["line1", "Address line 1", 200],
            ["line2", "Address line 2 or landmark (optional)", 200],
            ["city", "City", 100],
            ["state", "State", 100],
            ["pin", "PIN code", 6],
          ].map(([key, label, max]) => (
            <div key={key} className="space-y-2">
              <Label htmlFor={`address-${key}`}>{label}</Label>
              <Input
                id={`address-${key}`}
                value={form[key]}
                required={key !== "line2"}
                maxLength={max}
                pattern={key === "pin" ? "[0-9]{6}" : undefined}
                inputMode={key === "pin" ? "numeric" : undefined}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <p className="text-sm text-muted-foreground">Country: India</p>
          {["pickup", "delivery"].map((kind) => (
            <label key={kind} className="flex items-center gap-3 min-h-11">
              <input
                type="checkbox"
                checked={form[`default_${kind}`]}
                onChange={(e) =>
                  setForm({ ...form, [`default_${kind}`]: e.target.checked })
                }
              />
              Default {kind} address
            </label>
          ))}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button disabled={busy} type="submit">
              {busy ? "Saving…" : "Save address"}
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
        </form>
      </DialogContent>
    </Dialog>
  );
}
