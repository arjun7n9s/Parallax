import { type ReactNode } from "react";
import { cn, fmt } from "../../lib/utils";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

interface KpiProps {
  eyebrow: string;
  value: number | string;
  unit?: string;
  delta?: number; // -100 to 100, in percent
  trend?: number[]; // 7-14 points for sparkline
  size?: "sm" | "md" | "lg";
  formatter?: (n: number) => string;
  emphasis?: "bone" | "ink" | "oxblood" | "acid";
  children?: ReactNode;
}

const emphasisClass: Record<string, string> = {
  bone: "bg-bone-50 text-ink",
  ink: "bg-ink text-bone",
  oxblood: "bg-oxblood text-bone",
  acid: "bg-acid text-ink",
};

const sizeClass = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

const valueSize = {
  sm: "text-2xl",
  md: "text-4xl",
  lg: "text-6xl",
};

export function Kpi({
  eyebrow,
  value,
  unit,
  delta,
  trend,
  size = "md",
  formatter,
  emphasis = "bone",
  children,
}: KpiProps) {
  const formatted =
    typeof value === "number" ? (formatter ? formatter(value) : fmt(value)) : value;
  const deltaInfo =
    delta !== undefined && delta !== null
      ? delta > 0
        ? { Icon: ArrowUpRight, color: "text-acid" }
        : delta < 0
        ? { Icon: ArrowDownRight, color: "text-danger" }
        : { Icon: Minus, color: "text-ink/40" }
      : null;

  return (
    <div className={cn("relative flex flex-col", emphasisClass[emphasis], sizeClass[size])}>
      <div className={cn("eyebrow mb-3", emphasis === "bone" ? "text-ink/60" : "text-bone/60")}>
        {eyebrow}
      </div>
      <div className="flex items-baseline gap-2">
        <div className={cn("font-display tabular-nums leading-none tracking-tight", valueSize[size])}>
          {formatted}
        </div>
        {unit && (
          <div className={cn("font-mono text-sm", emphasis === "bone" ? "text-ink/50" : "text-bone/50")}>
            {unit}
          </div>
        )}
      </div>

      {(deltaInfo || trend) && (
        <div className="mt-4 flex items-center justify-between gap-3">
          {deltaInfo && (
            <div className={cn("flex items-center gap-1 font-mono text-xs", deltaInfo.color)}>
              <deltaInfo.Icon className="w-3.5 h-3.5" strokeWidth={2.5} />
              <span>{delta! > 0 ? "+" : ""}{delta}%</span>
            </div>
          )}
          {trend && trend.length > 1 && (
            <div className="flex-1 max-w-[120px]">
              <Sparkline
                points={trend}
                stroke={emphasis === "bone" ? "#0A0A0A" : "#F4F1EA"}
              />
            </div>
          )}
        </div>
      )}

      {children && <div className="mt-3">{children}</div>}
    </div>
  );
}

/** SVG sparkline, no axis, no labels. */
function Sparkline({ points, stroke = "#0A0A0A" }: { points: number[]; stroke?: string }) {
  if (points.length < 2) return null;
  const w = 120, h = 32, pad = 2;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = (w - pad * 2) / (points.length - 1);
  const path = points
    .map((p, i) => {
      const x = pad + i * step;
      const y = pad + (h - pad * 2) * (1 - (p - min) / range);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-8 overflow-visible" preserveAspectRatio="none">
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="square" />
      <circle
        cx={pad + (points.length - 1) * step}
        cy={pad + (h - pad * 2) * (1 - (points[points.length - 1] - min) / range)}
        r="2"
        fill={stroke}
      />
    </svg>
  );
}
