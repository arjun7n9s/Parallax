import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Brain,
  ChevronRight,
  Clock,
  FileSearch,
  Filter,
  Plus,
  Search,
  Shield,
  Sparkles,
  Terminal,
  Upload,
  Zap,
} from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Kpi } from "../components/primitives/Kpi";
import { Pill, VerdictPill } from "../components/primitives/Pill";
import { Distribution } from "../components/primitives/Graph";
import { getKpi, getRecentEvents, getRecentFamilies, getSubmissions } from "../lib/api";
import { type Submission } from "../lib/mock-data";
import { cn, dur, fmt, pct, relTime, riskColor, shortHash } from "../lib/utils";

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.04, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] },
  }),
};

export default function Console() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [kpi, setKpi] = useState<Awaited<ReturnType<typeof getKpi>> | null>(null);
  const [families, setFamilies] = useState<Awaited<ReturnType<typeof getRecentFamilies>>>([]);
  const [events, setEvents] = useState<Awaited<ReturnType<typeof getRecentEvents>>>([]);
  const [filter, setFilter] = useState<"all" | "critical" | "high" | "review">("all");
  const navigate = useNavigate();

  useEffect(() => {
    void (async () => {
      setSubmissions((await getSubmissions(1, 12)).items);
      setKpi(await getKpi());
      setFamilies(await getRecentFamilies());
      setEvents(await getRecentEvents());
    })();
  }, []);

  const filtered = submissions.filter((s) => {
    if (filter === "all") return true;
    if (filter === "critical") return s.riskScore >= 9;
    if (filter === "high") return s.riskScore >= 7;
    if (filter === "review") return s.riskScore >= 4 && s.riskScore < 7;
    return true;
  });

  return (
    <div>
      <Topbar
        eyebrow="Analyst Console"
        title="Submissions"
        right={
          <>
            <Link to="/hunt" className="btn h-9 px-3 text-xs">
              <FileSearch className="w-3.5 h-3.5" />
              Hunt
            </Link>
            <button className="btn-primary h-9 px-3 text-xs">
              <Plus className="w-3.5 h-3.5" />
              New submission
            </button>
          </>
        }
      />

      <div className="p-6 space-y-6 max-w-[1600px]">
        {/* ============ KPI Row ============ */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-ink/20 border border-ink/10">
          <motion.div custom={0} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi
              eyebrow="Total Submissions"
              value={kpi?.totalSubmissions ?? 0}
              trend={kpi?.trend}
              emphasis="bone"
            />
          </motion.div>
          <motion.div custom={1} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi
              eyebrow="Active Threats"
              value={kpi?.activeThreats ?? 0}
              delta={12}
              trend={[8, 12, 9, 14, 18, 16, 18]}
              emphasis="oxblood"
            />
          </motion.div>
          <motion.div custom={2} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi
              eyebrow="Avg. Risk Score"
              value={kpi ? kpi.avgRiskScore : 0}
              formatter={(n) => n.toFixed(1)}
              unit="/ 10"
              trend={[3.2, 3.5, 3.4, 3.7, 3.9, 3.6, 3.8]}
              emphasis="bone"
            />
          </motion.div>
          <motion.div custom={3} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi
              eyebrow="IOCs Discovered"
              value={kpi?.iocsDiscovered ?? 0}
              delta={4}
              trend={[240, 256, 268, 280, 290, 305, 312]}
              emphasis="bone"
            />
          </motion.div>
        </div>

        {/* ============ Main grid ============ */}
        <div className="grid grid-cols-12 gap-6">
          {/* Left: Submissions */}
          <div className="col-span-12 xl:col-span-8 space-y-6">
            {/* Submit zone */}
            <motion.div
              custom={0}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              className="border-2 border-dashed border-ink/30 hover:border-ink hover:bg-ink/3 transition-colors p-8 flex items-center justify-between gap-6 group"
            >
              <div>
                <div className="eyebrow mb-1.5">Drop an APK to begin</div>
                <div className="font-display text-2xl">Submit for analysis</div>
                <div className="font-mono text-xs text-ink/60 mt-1">
                  .apk · up to 250 MB · auto-hashes, auto-triages, auto-routes
                </div>
              </div>
              <button className="btn-primary h-12 px-6">
                <Upload className="w-4 h-4" />
                Choose file
              </button>
            </motion.div>

            {/* Submissions list */}
            <motion.div
              custom={1}
              initial="hidden"
              animate="show"
              variants={fadeUp}
            >
              <Panel>
                <div className="px-6 pt-5 pb-3 flex items-end justify-between gap-4 flex-wrap">
                  <PanelHeader
                    eyebrow="Queue"
                    title="Recent submissions"
                    right={
                      <div className="flex items-center gap-2">
                        <Filter className="w-3.5 h-3.5 text-ink/40" strokeWidth={1.6} />
                        {(["all", "critical", "high", "review"] as const).map((f) => (
                          <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={cn(
                              "h-7 px-2.5 text-[10px] font-mono uppercase tracking-widest border transition-colors",
                              filter === f
                                ? "border-ink bg-ink text-bone"
                                : "border-ink/20 text-ink/60 hover:text-ink hover:border-ink/40"
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
                  <div>Package</div>
                  <div>Verdict</div>
                  <div>Risk</div>
                  <div>IOCs</div>
                  <div>Duration</div>
                  <div>Submitted</div>
                  <div></div>
                </div>

                <div>
                  {filtered.length === 0 ? (
                    <EmptyState />
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
                            {shortHash(s.sha256)} · {(s.sizeBytes / 1024 / 1024).toFixed(1)} MB
                            {s.family && (
                              <>
                                <span className="mx-1.5">·</span>
                                <span className="text-oxblood">{s.family}</span>
                              </>
                            )}
                          </div>
                        </div>
                        <div>
                          {s.verdict && <VerdictPill verdict={s.verdict} pulse={s.status === "running"} />}
                          {s.status === "running" && !s.verdict && <Pill tone="muted">Running</Pill>}
                        </div>
                        <div>
                          <RiskBar score={s.riskScore} />
                        </div>
                        <div className="font-mono text-xs text-ink">{s.iocs}</div>
                        <div className="font-mono text-xs text-ink/70">{dur(s.durationMs)}</div>
                        <div className="font-mono text-xs text-ink/50">{relTime(s.submittedAt)}</div>
                        <div>
                          <ChevronRight className="w-4 h-4 text-ink/40" strokeWidth={1.6} />
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </Panel>
            </motion.div>
          </div>

          {/* Right: Side widgets */}
          <div className="col-span-12 xl:col-span-4 space-y-6">
            {/* Top families */}
            <motion.div custom={0} initial="hidden" animate="show" variants={fadeUp}>
              <Panel>
                <PanelHeader
                  eyebrow="Top families (7d)"
                  title="Identified"
                />
                <div className="px-6 pb-5">
                  <Distribution
                    items={families.map((f, i) => ({
                      label: f.family,
                      value: f.count,
                      color: i === 0 ? "#7C1F2D" : i < 3 ? "#0A0A0A" : "#0A0A0A66",
                    }))}
                  />
                </div>
              </Panel>
            </motion.div>

            {/* Cost */}
            <motion.div custom={1} initial="hidden" animate="show" variants={fadeUp}>
              <Panel variant="ink">
                <PanelHeader
                  eyebrow={<span className="text-bone/60">Cost guard</span>}
                  title={<span className="text-bone">$0.16 / APK</span>}
                  right={
                    <Link to="/cost" className="text-bone/60 hover:text-bone">
                      <BarChart3 className="w-4 h-4" strokeWidth={1.6} />
                    </Link>
                  }
                />
                <div className="px-6 pb-6 grid grid-cols-2 gap-4">
                  <Metric label="Today" value="$24.18" sub="of $50 budget" />
                  <Metric label="This hour" value="$1.84" sub="12 analyses" />
                  <Metric label="Avg. tokens" value="42.1k" sub="per APK" />
                  <Metric label="Cache hit" value="63%" sub="prompt cache" />
                </div>
              </Panel>
            </motion.div>

            {/* Activity feed */}
            <motion.div custom={2} initial="hidden" animate="show" variants={fadeUp}>
              <Panel>
                <PanelHeader
                  eyebrow="Live activity"
                  title="Stream"
                  right={
                    <div className="flex items-center gap-1.5">
                      <span className="live-dot" />
                      <span className="eyebrow text-ink/50">REC</span>
                    </div>
                  }
                />
                <ul className="px-6 pb-5 space-y-2.5 max-h-[320px] overflow-auto">
                  {events.map((e, i) => (
                    <li key={i} className="flex items-start gap-3 font-mono text-xs">
                      <span className="text-ink/40 shrink-0 w-12">{e.time}</span>
                      <span className="text-ink/80 flex-1">{e.text}</span>
                      <span
                        className={cn(
                          "w-1.5 h-1.5 rounded-full shrink-0 mt-1.5",
                          e.kind === "danger" ? "bg-oxblood" : e.kind === "warn" ? "bg-warn" : "bg-acid"
                        )}
                      />
                    </li>
                  ))}
                </ul>
              </Panel>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}

const GRID_COLS = "minmax(220px, 1.7fr) 110px 130px 60px 90px 110px 30px";

function RiskBar({ score }: { score: number }) {
  const tone = riskColor(score);
  const fill = tone === "ok" ? "bg-ok" : tone === "warn" ? "bg-warn" : "bg-oxblood";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-ink/10 relative overflow-hidden">
        <div className={cn("absolute inset-y-0 left-0", fill)} style={{ width: `${score * 10}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums text-ink/80 w-7">{score.toFixed(1)}</span>
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <div className="eyebrow text-bone/50 mb-1.5">{label}</div>
      <div className="font-display text-2xl leading-none">{value}</div>
      <div className="font-mono text-[10px] text-bone/50 mt-1">{sub}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="px-6 py-16 flex flex-col items-center text-center">
      <div className="w-12 h-12 border border-ink/20 flex items-center justify-center mb-3">
        <Search className="w-5 h-5 text-ink/40" strokeWidth={1.4} />
      </div>
      <div className="font-display text-xl mb-1">No submissions match.</div>
      <div className="font-mono text-xs text-ink/50">Try a different filter, or submit a new APK.</div>
    </div>
  );
}
