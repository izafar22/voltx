import { motion } from "framer-motion";

export const ChargingRing = ({ soc = 0, active = true, size = 260 }) => {
  const stroke = 14;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (soc / 100) * c;
  return (
    <div className="relative" style={{ width: size, height: size }} data-testid="charging-ring">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} className="stroke-secondary" fill="none" />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} strokeLinecap="round"
          className="stroke-charging" fill="none"
          strokeDasharray={c}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      {active && <div className="absolute inset-4 rounded-full bg-charging/10 animate-pulse-ring" />}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-5xl font-light tabular tracking-tighter">{soc}%</span>
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground mt-1">Charged</span>
      </div>
    </div>
  );
};
