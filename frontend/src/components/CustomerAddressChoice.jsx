import { addressText } from "../lib/customerProfile";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

export function CustomerAddressChoice({
  label,
  value,
  addresses,
  onChange,
  disabled,
}) {
  return (
    <div className="space-y-2 min-w-0">
      <Label>{label}</Label>
      <Select
        value={value || "later"}
        onValueChange={(v) => onChange(v === "later" ? null : v)}
        disabled={disabled}
      >
        <SelectTrigger
          aria-label={label}
          className="h-auto min-h-11 text-left [&>span]:whitespace-normal [&>span]:break-words"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="later">Choose later</SelectItem>
          {addresses.map((a) => (
            <SelectItem key={a.id} value={a.id}>
              {addressText(a)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
