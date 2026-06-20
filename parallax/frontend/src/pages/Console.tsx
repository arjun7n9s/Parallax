import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ChevronRight, Filter, Loader2, RefreshCw, Search, Upload } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Kpi } from "../components/primitives/Kpi";
import { Pill, VerdictPill } from "../components/primitives/Pill";
import { Distribution } from "../components/primitives/Graph";
import {
  getKpi,
  getRecentFamilies,
  getSubmissions,
  isDemo,
  streamHistory,
  submitApk,
  type Submission,
} from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { cn, dur, relTime, riskColor, shortHash } from "../lib/utils";

const GRID_COLS = "minmax(220px, 1.7fr) 110px 140px 60px 90px 110px 30px";
const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { duration: 0.4, delay: i * 0.03 } }),
};

export default function Console() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<"all" | "critical" | "high" | "review">("all");
  const [live, setLive] = useState<Submission[] | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitErr, setSubmitErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const list = useAsync(() => getSubmissions(1, 24), []);
  const kpi = useAsync(getKpi, []);
  const families = useAsync(getRecentFamilies, []);

  // Live updates via SSE (no-op in demo) — overlays the fetched page.
  useEffect(() => streamHistory(setLive), []);

  const submissions = live ?? list.data?.items ?? [];
  const filtered = submissions.filter((s) => {
    if (filter === "critical") return s.verdict === "CRITICAL";
    if (filter === "high") return s.verdict === "HIGH";
    if (filter === "review") return s.verdict === "MEDIUM" || s.verdict === "LOW";
    return true;
  });

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSubmitErr(null);
    setSubmitting(true);
    try {
      const res = await submitApk(file);
      list.reload();
      navigate(`/console/${res.id}`);
    } catch (err) {
      setSubmitErr(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const verdictMix = (["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAN"] as const).map((v) => ({
    label: v,
    value: submissions.filter((s) => s.verdict === v).length,
    color: v === "CRITICAL" || v === "HIGH" ? "#7C1F2D" : v === "MEDIUM" ? "#C9923A" : "#0A0A0A66",
  }));

  return (
    <div>
      <Topbar
        eyebrow="Analyst Console"
        title="Submissions"
        right={
          <>
            <Link to="/hunt" className="btn h-9 px-3 text-xs">
              <Search className="w-3.5 h-3.5" /> Hunt
            </Link>
            <button onClick={() => fileRef.current?.click()} disabled={submitting} className="btn-primary h-9 px-3 text-xs">
              {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              New submission
            </button>
          </>
        }
      />
      <input ref={fileRef} type="file" accept=".apk" className="hidden" onChange={onFile} />

      <div className="p-6 space-y-6 max-w-[1600px]">
        {(submitErr || (!isDemo() && list.error)) && (
          <Banner
            tone={submitErr ? "danger" : "warn"}
            text={submitErr ?? `${list.error} — showing what's available. Check the backend / API key in Settings.`}
            onRetry={list.error ? list.reload : undefined}
          />
        )}

        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-ink/20 border border-ink/10">
          <Kpi eyebrow="Total Submissions" value={kpi.data?.totalSubmissions ?? 0} emphasis="bone" />
          <Kpi eyebrow="Active Threats" value={kpi.data?.activeThreats ?? 0} emphasis="oxblood" />
          <Kpi
            eyebrow="Avg. Risk Score"
            value={kpi.data?.avgRiskScore ?? 0}
            formatter={(n) => n.toFixed(0)}
            unit="/ 100"
            emphasis="bone"
          />
          <Kpi eyebrow="IOCs Discovered" value={kpi.data?.iocsDiscovered ?? 0} emphasis="bone" />
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 xl:col-span-8 space-y-6">
            {/* Submit dropzone */}
            <button
              onClick={() => fileRef.current?.click()}
              disabled={submitting}
              className="w-full border-2 border-dashed border-ink/30 hover:border-ink hover:bg-ink/[0.03] transition-colors p-8 flex items-center justify-between gap-6 text-left"
            >
              <div>
                <div className="eyebrow mb-1.5">Drop an APK to begin</div>
                <div className="font-display text-2xl">Submit for analysis</div>
                <div className="font-mono text-xs text-ink/60 mt-1">.apk · up to 250 MB · auto-hashes, triages, and routes through the pipeline</div>
              </div>
              <span className="btn-primary h-12 px-6 pointer-events-none">
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                Choose file
              </span>
            </button>

            {/* Submissions list */}
            <Panel>
              <div className="px-6 pt-5 pb-3">
                <PanelHeader
                  eyebrow={live ? "Queue · live" : "Queue"}
                  title="Recent submissions"
                  right={
                    <div className="flex items-center gap-2">
                      <button onClick={list.reload} className="btn-icon w-7 h-7" title="Refresh">
                        <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.6} />
                      </button>
                      <Filter className="w-3.5 h-3.5 text-ink/40" strokeWidth={1.6} />
                      {(["all", "critical", "high", "review"] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setFilter(f)}
                          className={cn(
                            "h-7 px-2.5 text-[10px] font-mono uppercase tracking-widest border transition-colors",
                            filter === f ? "border-ink bg-ink text-bone" : "border-ink/20 text-ink/60 hover:text-ink hover:border-ink/40"
                          )}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  }
                />
              </div>

              <div className="grid-header" style={{ gridTemplateColumns: GRID_COLS }}>
                <div>Package</div><div>Verdict</div><div>Risk</div><div>IOCs</div><div>Duration</div><div>Submitted</div><div></div>
              </div>

              {list.loading && !live ? (
                <ListSkeleton />
              ) : filtered.length === 0 ? (
                <EmptyState live={!!live} hasAny={submissions.length > 0} />
              ) : (
                filtered.map((s, i) => (
                  <motion.div
                    key={s.id}
                    custom={i}
                    initial="hidden"
                    animate="show"
                    variants={fadeUp}
                    onClick={() => navigate(`/console/${s.id}`)}
                    className="grid-row"
                    style={{ gridTemplateColumns: GRID_COLS }}
                  >
                    <div className="min-w-0">
                      <div className="font-mono text-xs text-ink truncate flex items-center gap-1.5">
                        {s.status === "running" && <span className="live-dot" />}
                        {s.packageName}
                      </div>
                      <div className="font-mono text-[10px] text-ink/50 mt-0.5">
                        {shortHash(s.sha256)}
                        {s.sizeBytes > 0 && ` · ${(s.sizeBytes / 1024 / 1024).toFixed(1)} MB`}
                        {s.family && <span className="text-oxblood"> · {s.family}</span>}
                      </div>
                    </div>
                    <div>
                      {s.verdict ? (
                        <VerdictPill verdict={s.verdict} pulse={s.status === "running"} />
                      ) : (
                        <Pill tone="muted" pulse={s.status === "running"}>{s.stage}</Pill>
                      )}
                    </div>
                    <div><RiskBar score={s.riskScore} /></div>
                    <div className="font-mono text-xs text-ink">{s.iocs}</div>
                    <div className="font-mono text-xs text-ink/70">{s.durationMs ? dur(s.durationMs) : "—"}</div>
                    <div className="font-mono text-xs text-ink/50">{relTime(s.submittedAt)}</div>
                    <div><ChevronRight className="w-4 h-4 text-ink/40" strokeWidth={1.6} /></div>
                  </motion.div>
                ))
              )}
            </Panel>
          </div>

          {/* Right rail */}
          <div className="col-span-12 xl:col-span-4 space-y-6">
            <Panel>
              <PanelHeader eyebrow="Top families" title="Identified" />
              <div className="px-6 pb-5">
                {families.loading ? (
                  <div className="font-mono text-xs text-ink/40 py-6">Loading…</div>
                ) : (families.data?.length ?? 0) === 0 ? (
                  <div className="font-mono text-xs text-ink/40 py-6">No family attributions yet.</div>
                ) : (
                  <Distribution
                    items={(families.data ?? []).map((f, i) => ({
                      label: f.family,
                      value: f.count,
                      color: i === 0 ? "#7C1F2D" : i < 3 ? "#0A0A0A" : "#0A0A0A66",
                    }))}
                  />
                )}
              </div>
            </Panel>

            <Panel>
              <PanelHeader eyebrow="This page" title="Verdict mix" />
              <div className="px-6 pb-5">
                {submissions.length === 0 ? (
                  <div className="font-mono text-xs text-ink/40 py-6">No submissions yet.</div>
                ) : (
                  <Distribution items={verdictMix.filter((v) => v.value > 0)} />
                )}
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}

function RiskBar({ score }: { score: number }) {
  const tone = riskColor(score);
  const fill = tone === "ok" ? "bg-ok" : tone === "warn" ? "bg-warn" : "bg-oxblood";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-ink/10 relative overflow-hidden">
        <div className={cn("absolute inset-y-0 left-0", fill)} style={{ width: `${Math.min(100, score)}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums text-ink/80 w-8">{score.toFixed(0)}</span>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="divide-y divide-ink/5">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-[52px] px-6 flex items-center">
          <div className="h-3 bg-ink/10 animate-pulse" style={{ width: `${30 + (i % 4) * 12}%` }} />
        </div>
      ))}
    </div>
  );
}

function EmptyState({ live, hasAny }: { live: boolean; hasAny: boolean }) {
  return (
    <div className="px-6 py-16 flex flex-col items-center text-center">
      <div className="w-12 h-12 border border-ink/20 flex items-center justify-center mb-3">
        <Search className="w-5 h-5 text-ink/40" strokeWidth={1.4} />
      </div>
      <div className="font-display text-xl mb-1">{hasAny ? "No submissions match." : "No submissions yet."}</div>
      <div className="font-mono text-xs text-ink/50">
        {hasAny ? "Try a different filter." : live ? "Waiting for the first analysis…" : "Submit an APK to begin."}
      </div>
    </div>
  );
}

function Banner({ tone, text, onRetry }: { tone: "danger" | "warn"; text: string; onRetry?: () => void }) {
  return (
    <div className={cn("flex items-center justify-between gap-3 border p-3 font-mono text-xs", tone === "danger" ? "border-oxblood/40 bg-oxblood/5 text-oxblood" : "border-warn/40 bg-warn/5 text-ink/80")}>
      <span>{text}</span>
      {onRetry && (
        <button onClick={onRetry} className="shrink-0 underline hover:no-underline">retry</button>
      )}
    </div>
  );
}
