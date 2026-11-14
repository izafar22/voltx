import { PRODUCT_NAME } from "../config/brand";
import { Zap } from "lucide-react";

export const Logo = ({ compact = false }) => (
  <div className="flex items-center gap-2" data-testid="logo">
    <div className="h-8 w-8 rounded-lg bg-charging flex items-center justify-center">
      <Zap className="h-5 w-5 text-black" fill="currentColor" strokeWidth={1.5} />
    </div>
    {!compact && <span className="font-display font-bold text-lg tracking-tight">{PRODUCT_NAME}</span>}
  </div>
);
