import { PRODUCT_NAME } from "../config/brand";
import rushxMark from "../assets/brand/rushx-mark.svg";

export const Logo = ({ compact = false }) => (
  <div
    className="flex items-center gap-2"
    data-testid="logo"
    role={compact ? "img" : undefined}
    aria-label={compact ? PRODUCT_NAME : undefined}
  >
    <img className="h-8 w-8" src={rushxMark} alt="" aria-hidden="true" />
    {!compact && <span className="font-display font-bold text-lg tracking-tight">{PRODUCT_NAME}</span>}
  </div>
);
