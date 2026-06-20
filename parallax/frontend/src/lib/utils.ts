import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Combine class names with tailwind-merge to dedupe conflicts. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a number as locale string with max N decimals. */
export function fmt(n: number, decimals = 0): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Format a number as a 2-decimal float. */
export function fmt2(n: number): string {
  return fmt(n, 2);
}

/** Format a percentage. */
export function pct(n: number, decimals = 0): string {
  return `${n.toFixed(decimals)}%`;
}

/** Truncate long strings with ellipsis. */
export function truncate(s: string, n = 64): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + "…";
}

/** Format a SHA-256 hash (or any hex string) with shortened middle. */
export function shortHash(s: string, head = 8, tail = 6): string {
  if (s.length <= head + tail + 1) return s;
  return `${s.slice(0, head)}…${s.slice(-tail)}`;
}

/** Format a duration in ms as "1.2s" or "340ms". */
export function dur(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/** Format a relative timestamp like "2m ago", "1h ago". */
export function relTime(isoOrDate: string | Date): string {
  const t = typeof isoOrDate === "string" ? new Date(isoOrDate).getTime() : isoOrDate.getTime();
  const diff = Date.now() - t;
  const s = Math.floor(diff / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Risk-level color resolver. 0=safe, 1-3=low, 4-6=med, 7-9=high, 10=critical. */
export function riskColor(score: number): "ok" | "warn" | "danger" {
  if (score <= 3) return "ok";
  if (score <= 6) return "warn";
  return "danger";
}

/** Risk-level label. */
export function riskLabel(score: number): string {
  if (score <= 3) return "Clean";
  if (score <= 6) return "Suspicious";
  if (score <= 8) return "Malicious";
  return "Critical";
}

/** Verdict pill class. */
export function verdictPill(v: string): string {
  const upper = v.toUpperCase();
  if (upper === "CLEAN" || upper === "OK") return "pill-ok";
  if (upper === "SUSPICIOUS" || upper === "PENDING") return "pill-warn";
  if (upper === "MALICIOUS" || upper === "CRITICAL") return "pill-danger";
  return "pill-muted";
}
