import { type ReactNode } from "react";
import { cn, verdictPill } from "../../lib/utils";

type Tone = "ok" | "warn" | "danger" | "muted" | "ink" | "acid" | "bone" | "oxblood";

interface PillProps {
  tone?: Tone;
  children: ReactNode;
  className?: string;
  pulse?: boolean;
}

const toneClass: Record<Tone, string> = {
  ok: "pill-ok",
  warn: "pill-warn",
  danger: "pill-danger",
  muted: "pill-muted",
  ink: "pill-ink",
  acid: "pill-acid",
  bone: "pill-bone",
  oxblood: "pill-oxblood",
};

export function Pill({ tone = "muted", children, className, pulse = false }: PillProps) {
  return (
    <span className={cn(toneClass[tone], className)}>
      {pulse && <span className="live-dot" />}
      {children}
    </span>
  );
}

export function VerdictPill({ verdict, pulse = false }: { verdict: string; pulse?: boolean }) {
  return (
    <span className={verdictPill(verdict)}>
      {pulse && <span className="live-dot" />}
      {verdict}
    </span>
  );
}
