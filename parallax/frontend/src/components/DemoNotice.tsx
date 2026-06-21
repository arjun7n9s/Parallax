import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Info, X } from "lucide-react";
import { Dialog } from "./primitives/Dialog";
import { isDemo } from "../lib/api";

/**
 * Demo-awareness for the console. In demo mode the data is seeded and read-only,
 * so any action that requires the live backend (submitting an APK, downloading
 * artifacts, signing a quarantine URL, changing settings) is intercepted with a
 * clear explanation instead of 404ing or erroring.
 *
 * `guard(label)` returns true when the action may proceed (authenticated /
 * non-demo) and false when it was blocked — in which case a dialog is shown.
 */
const GuardCtx = createContext<(label?: string) => boolean>(() => true);

export function DemoGuardProvider({ children }: { children: ReactNode }) {
  const [blocked, setBlocked] = useState<string | null>(null);

  const guard = (label?: string): boolean => {
    if (isDemo()) {
      setBlocked(label ?? "This action");
      return false;
    }
    return true;
  };

  return (
    <GuardCtx.Provider value={guard}>
      {children}
      <Dialog open={!!blocked} onClose={() => setBlocked(null)} title="Demo mode">
        <p className="text-sm text-ink/80 leading-relaxed">
          <strong>{blocked}</strong> runs against the live PARALLAX backend and needs an
          authenticated analyst key. This public demo is <strong>seeded, read-only and
          rate-limited</strong> — APK submission, artifact downloads, signed-URL access and
          settings are disabled here.
        </p>
        <p className="text-sm text-ink/60 leading-relaxed mt-3">
          Everything you see is real PARALLAX output captured from live runs — you just can't
          trigger new backend work without a key.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={() => setBlocked(null)} className="btn h-10 px-4">
            Keep exploring
          </button>
          <Link to="/auth" onClick={() => setBlocked(null)} className="btn-primary h-10 px-4">
            Analyst console
          </Link>
        </div>
      </Dialog>
    </GuardCtx.Provider>
  );
}

export function useDemoGuard() {
  return useContext(GuardCtx);
}

/** Slim, dismissible banner shown across the console while in demo mode. */
export function DemoBanner() {
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => {
    setDismissed(sessionStorage.getItem("parallax.demoBannerDismissed") === "1");
  }, []);
  if (!isDemo() || dismissed) return null;
  return (
    <div className="flex items-center gap-3 px-6 h-9 bg-acid/90 text-ink border-b border-ink/15">
      <Info className="w-3.5 h-3.5 shrink-0" strokeWidth={2} />
      <p className="font-mono text-[11px] leading-none truncate">
        <strong className="uppercase tracking-widest">Demo</strong>
        <span className="mx-2 opacity-50">·</span>
        seeded, read-only data — submission, downloads &amp; exports need an authenticated key
        (rate-limited in production).
      </p>
      <Link to="/auth" className="ml-auto shrink-0 font-mono text-[10px] uppercase tracking-widest underline hover:no-underline">
        Get access
      </Link>
      <button
        onClick={() => {
          sessionStorage.setItem("parallax.demoBannerDismissed", "1");
          setDismissed(true);
        }}
        className="shrink-0 text-ink/60 hover:text-ink"
        aria-label="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
