import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Filter, Network, Search } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Pill } from "../components/primitives/Pill";
import { threatHunt } from "../lib/api";
import { type ThreatHuntHit } from "../lib/mock-data";
import { cn, relTime } from "../lib/utils";

export default function ThreatHunt() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [hits, setHits] = useState<ThreatHuntHit[]>([]);
  const [type, setType] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    void (async () => {
      const r = await threatHunt(q);
      if (mounted) setHits(r.hits);
    })();
    return () => {
      mounted = false;
    };
  }, [q]);

  const visible = type ? hits.filter((h) => h.type === type) : hits;

  return (
    <div>
      <Topbar eyebrow="Threat Intel" title="Hunt" />
      <div className="p-6 max-w-[1600px] space-y-6">
        <Panel>
          <div className="px-6 py-5 flex items-center gap-4 flex-wrap">
            <div className="flex-1 min-w-[280px] relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink/40" strokeWidth={1.6} />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search IPs, hashes, domains, C2 endpoints, ATT&CK techniques…"
                className="input pl-10"
                autoFocus
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-ink/40" strokeWidth={1.6} />
              {(["ip", "domain", "hash", "url", "permission"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setType(type === t ? null : t)}
                  className={cn(
                    "h-7 px-2.5 text-[10px] font-mono uppercase tracking-widest border transition-colors",
                    type === t
                      ? "border-ink bg-ink text-bone"
                      : "border-ink/20 text-ink/60 hover:text-ink hover:border-ink/40"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="Matches"
            title={`${visible.length} indicators`}
            right={
              <span className="font-mono text-[10px] uppercase tracking-widest text-ink/50">
                cross-submission IOC index
              </span>
            }
          />
          <div className="grid-header" style={{ gridTemplateColumns: "100px 1.6fr 1fr 1.2fr 1fr 100px 80px" }}>
            <div>Severity</div>
            <div>Indicator</div>
            <div>Family</div>
            <div>Matched in</div>
            <div>Type</div>
            <div>First seen</div>
            <div></div>
          </div>
          <div>
            {visible.map((h, i) => (
              <motion.div
                key={h.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3, delay: i * 0.02 }}
                className="grid-row"
                style={{ gridTemplateColumns: "100px 1.6fr 1fr 1.2fr 1fr 100px 80px" }}
              >
                <div>
                  <Pill tone={h.severity === "critical" ? "danger" : h.severity === "high" ? "warn" : "muted"}>
                    {h.severity}
                  </Pill>
                </div>
                <div className="font-mono text-xs text-ink truncate">{h.indicator}</div>
                <div className="font-mono text-xs text-oxblood truncate">{h.family}</div>
                <div className="font-mono text-xs text-ink/60 truncate">{h.matchedIn}</div>
                <div className="font-mono text-xs text-ink/60">{h.type}</div>
                <div className="font-mono text-xs text-ink/50">{relTime(h.firstSeen)}</div>
                <div>
                  <button
                    onClick={() => navigate(h.matchedIn?.startsWith("sub_") ? `/console/${h.matchedIn.split(",")[0].trim()}` : "/graph")}
                    title="View in graph / open submission"
                    className="btn-icon w-8 h-8"
                  >
                    <Network className="w-3.5 h-3.5" strokeWidth={1.6} />
                  </button>
                </div>
              </motion.div>
            ))}
            {visible.length === 0 && (
              <div className="px-6 py-16 text-center font-mono text-xs text-ink/50">
                No matches.
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
