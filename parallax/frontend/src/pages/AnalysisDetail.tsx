import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Download,
  Loader2,
  Network,
  ShieldAlert,
} from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Kpi } from "../components/primitives/Kpi";
import { Pill, VerdictPill } from "../components/primitives/Pill";
import { CopyableText } from "../components/primitives/JsonView";
import { TAIGGraph, Distribution } from "../components/primitives/Graph";
import {
  artifactUrl,
  getResult,
  getSubmission,
  getTAIGGraph,
  quarantineUrl,
  streamAnalysis,
  type AnalysisResult,
  type Submission,
  type TAIGNodes,
} from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { useDemoGuard } from "../components/DemoNotice";
import { cn, dur, relTime, riskColor, riskLabel } from "../lib/utils";

type Tab = "overview" | "static" | "reasoning" | "evidence" | "graph";
const TABS: Tab[] = ["overview", "static", "reasoning", "evidence", "graph"];

export default function AnalysisDetail() {
  const { id = "" } = useParams();
  const guard = useDemoGuard();
  const [tab, setTab] = useState<Tab>("overview");
  const [liveSub, setLiveSub] = useState<Submission | null>(null);

  const subState = useAsync(() => getSubmission(id), [id]);
  const sub = liveSub ?? subState.data;
  const isDone = sub?.status === "complete";
  const resultState = useAsync<AnalysisResult | null>(() => (isDone ? getResult(id) : Promise.resolve(null)), [id, isDone]);
  const taig = useAsync(() => getTAIGGraph(id), [id, isDone]);

  // Live status while the analysis is still running.
  useEffect(() => {
    if (!sub || sub.status === "complete" || sub.status === "failed") return;
    return streamAnalysis(id, setLiveSub);
  }, [id, sub?.status]);

  if (subState.loading && !sub) return <CenterState><Loader2 className="w-4 h-4 animate-spin" /> Loading analysis…</CenterState>;
  if (subState.error || !sub)
    return (
      <CenterState>
        <ShieldAlert className="w-5 h-5 text-oxblood" />
        <div className="font-display text-xl mt-2">Analysis not found</div>
        <div className="font-mono text-xs text-ink/50 mt-1">{subState.error ?? `No submission ${id}`}</div>
        <Link to="/console" className="btn h-9 px-4 text-xs mt-4"><ArrowLeft className="w-3.5 h-3.5" /> Back to console</Link>
      </CenterState>
    );

  const result = resultState.data;

  return (
    <div>
      <Topbar
        title={sub.packageName}
        right={
          <>
            <Link to={`/graph?from=${sub.id}`} className="btn h-9 px-3 text-xs"><Network className="w-3.5 h-3.5" /> TAIG</Link>
            <button
              onClick={() => guard("Downloading the PDF report") && window.open(artifactUrl(sub.id, "report.pdf"), "_blank")}
              className="btn h-9 px-3 text-xs"
            >
              <Download className="w-3.5 h-3.5" /> Report
            </button>
          </>
        }
      >
        <div className="flex items-center gap-2 mb-3">
          <Link to="/console" className="font-mono text-[10px] uppercase tracking-widest text-ink/50 hover:text-ink">Submissions</Link>
          <span className="text-ink/30">/</span>
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink/70">{sub.id}</span>
        </div>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {sub.verdict ? <VerdictPill verdict={sub.verdict} pulse={sub.status === "running"} /> : <Pill tone="muted" pulse>{sub.stage}</Pill>}
            {sub.family && <Pill tone="oxblood">{sub.family}</Pill>}
            {sub.tags.map((t) => <Pill key={t} tone="bone">{t}</Pill>)}
            <span className="font-mono text-[10px] text-ink/50">· {relTime(sub.submittedAt)}</span>
          </div>
          <div className="font-mono text-[10px] text-ink/50">
            {sub.fileName}{sub.sizeBytes > 0 && ` · ${(sub.sizeBytes / 1024 / 1024).toFixed(2)} MB`}
          </div>
        </div>
      </Topbar>

      <div className="p-6 max-w-[1600px]">
        {!isDone && (
          <div className="mb-6 border border-ink/15 bg-bone-50 p-4 flex items-center gap-3 font-mono text-xs text-ink/70">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analysis in progress — stage <strong className="text-ink">{sub.stage}</strong>. This view updates live.
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-px bg-ink/20 border border-ink/10 mb-6">
          <Kpi eyebrow="Risk score" value={sub.riskScore} formatter={(n) => n.toFixed(0)} unit="/ 100" emphasis={riskColor(sub.riskScore) === "danger" ? "oxblood" : "bone"} />
          <Kpi eyebrow="Verdict" value={sub.verdict ?? "PENDING"} emphasis="bone" />
          <Kpi eyebrow="IOCs found" value={result?.iocs.length ?? sub.iocs} emphasis="bone" />
          <Kpi eyebrow="Duration" value={sub.durationMs ? dur(sub.durationMs) : "—"} emphasis="bone" />
          <Kpi eyebrow="Confidence" value={result?.confidence ? result.confidence.band.toUpperCase() : "—"} emphasis="bone" />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-px bg-ink/20 border border-ink/10 mb-6 overflow-x-auto">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} className={cn("h-10 px-5 font-mono text-[10px] uppercase tracking-widest transition-colors shrink-0", tab === t ? "bg-ink text-bone" : "bg-bone-50 text-ink/60 hover:text-ink")}>
              {t}
            </button>
          ))}
        </div>

        {!isDone ? (
          <Panel><div className="px-6 py-16 text-center font-mono text-xs text-ink/50">Detailed results appear once the analysis completes.</div></Panel>
        ) : resultState.loading ? (
          <CenterState><Loader2 className="w-4 h-4 animate-spin" /> Loading results…</CenterState>
        ) : !result ? (
          <Panel><div className="px-6 py-16 text-center font-mono text-xs text-ink/50">{resultState.error ?? "No result payload available."}</div></Panel>
        ) : (
          <>
            {tab === "overview" && <Overview sub={sub} r={result} />}
            {tab === "static" && <Static sub={sub} r={result} />}
            {tab === "reasoning" && <Reasoning r={result} />}
            {tab === "evidence" && <Evidence sub={sub} r={result} />}
            {tab === "graph" && <GraphView taig={taig.data} loading={taig.loading} />}
          </>
        )}
      </div>
    </div>
  );
}

function CenterState({ children }: { children: React.ReactNode }) {
  return <div className="min-h-[60vh] flex flex-col items-center justify-center text-center font-mono text-xs text-ink/60 gap-1">{children}</div>;
}

// ---------------- Overview ----------------
function Overview({ sub, r }: { sub: Submission; r: AnalysisResult }) {
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-8 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Executive summary" title="What happened" />
          <div className="px-6 pb-6 text-sm leading-relaxed text-ink/80">
            {r.executiveSummary || `${sub.packageName} scored ${sub.riskScore}/100 (${sub.verdict}).`}
          </div>
        </Panel>

        <Panel>
          <PanelHeader eyebrow="Investigation reasoning trace" title="Why this verdict" />
          {r.irt.length === 0 ? (
            <div className="px-6 pb-6 font-mono text-xs text-ink/50">No reasoning trace recorded.</div>
          ) : (
            <ul className="px-6 pb-6 space-y-3">
              {r.irt.map((e, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className={cn("mt-1.5 w-1.5 h-1.5 rounded-full shrink-0", e.status === "CONFIRMED" ? "bg-oxblood" : e.status === "REJECTED" ? "bg-ink/30" : "bg-warn")} />
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-widest text-ink/50">{e.status}</div>
                    <div className="text-sm text-ink font-medium">{e.claim}</div>
                    {e.explanation && <div className="text-sm text-ink/65 mt-0.5">{e.explanation}</div>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="col-span-12 lg:col-span-4 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Identity" title="Hashes" />
          <div className="px-6 pb-5 space-y-3 font-mono text-xs">
            <Row label="SHA-256"><CopyableText text={sub.sha256 || "—"} className="min-w-0 truncate" /></Row>
            <Row label="Size"><span>{sub.sizeBytes ? `${(sub.sizeBytes / 1024 / 1024).toFixed(2)} MB` : "—"}</span></Row>
            <Row label="Family"><span className="text-oxblood">{r.family ?? "unattributed"}{r.familyConfidence ? ` (${(r.familyConfidence * 100).toFixed(0)}%)` : ""}</span></Row>
            <Row label="Stage"><span>{sub.stage}</span></Row>
          </div>
        </Panel>

        {r.confidence && (
          <Panel variant={r.confidence.needsReview ? "ink" : "bone"}>
            <PanelHeader
              eyebrow={<span className={r.confidence.needsReview ? "text-bone/60" : "text-ink/60"}>Verdict confidence</span>}
              title={<span className={r.confidence.needsReview ? "text-bone" : "text-ink"}>{r.confidence.band.toUpperCase()} · {(r.confidence.score * 100).toFixed(0)}%</span>}
            />
            <div className={cn("px-6 pb-6 space-y-1.5 font-mono text-[11px]", r.confidence.needsReview ? "text-bone/75" : "text-ink/70")}>
              {r.confidence.needsReview && (
                <div className="flex items-center gap-1.5 mb-2 text-warn"><AlertTriangle className="w-3.5 h-3.5" /> Flagged for human review</div>
              )}
              {r.confidence.drivers.map((d, i) => <div key={i}>· {d}</div>)}
            </div>
          </Panel>
        )}

        {r.recommendations.length > 0 && (
          <Panel>
            <PanelHeader eyebrow="Recommended actions" title="Next steps" />
            <ul className="px-6 pb-6 space-y-2.5 font-mono text-xs">
              {r.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-acid shrink-0 mt-0.5" strokeWidth={2.2} />
                  <div>
                    <span className="text-ink/85">{rec.action}</span>
                    <Pill tone={rec.mode === "HELD" ? "danger" : rec.mode === "AUTO_LOW_RISK" ? "muted" : "bone"} className="ml-2">{rec.mode}</Pill>
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </div>
    </div>
  );
}

// ---------------- Static ----------------
function Static({ sub, r }: { sub: Submission; r: AnalysisResult }) {
  const comps = Object.entries(r.components).filter(([, v]) => v > 0);
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-6 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Manifest" title={`${sub.permissions.length} permissions`} />
          {sub.permissions.length === 0 ? (
            <div className="px-6 pb-5 font-mono text-xs text-ink/50">No permissions captured in the result payload.</div>
          ) : (
            <ul className="px-6 pb-5 space-y-1.5 font-mono text-xs">
              {sub.permissions.map((p) => (
                <li key={p} className="flex items-center justify-between gap-2">
                  <span className="text-ink/80">{p}</span>
                  {isDangerous(p) && <Pill tone="danger">abuse</Pill>}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-6 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Risk components" title="Weighted evidence" right={<span className="font-mono text-[10px] text-ink/50">evidence {r.evidenceScore.toFixed(0)} → {r.calibratedScore.toFixed(0)}</span>} />
          <div className="px-6 pb-5 space-y-2.5 font-mono text-xs">
            {comps.length === 0 ? (
              <div className="text-ink/50">No components scored above zero.</div>
            ) : comps.map(([k, v]) => (
              <div key={k}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-ink/70">{k.replace(/_/g, " ")}</span>
                  <span className="text-ink/50">{(v * 100).toFixed(0)}% · w{((r.weights[k] ?? 0) * 100).toFixed(0)}</span>
                </div>
                <div className="h-1.5 bg-ink/10"><div className="h-full bg-ink" style={{ width: `${v * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </Panel>
        {r.attck.length > 0 && (
          <Panel>
            <PanelHeader eyebrow="MITRE ATT&CK" title={`${r.attck.length} techniques`} />
            <div className="px-6 pb-5 flex flex-wrap gap-1.5">
              {r.attck.map((t) => <Pill key={t} tone="muted">{t}</Pill>)}
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}

function isDangerous(perm: string): boolean {
  return ["RECEIVE_SMS", "SEND_SMS", "READ_SMS", "BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "BIND_DEVICE_ADMIN", "REQUEST_INSTALL_PACKAGES"].some((d) => perm.includes(d));
}

// ---------------- Reasoning ----------------
function Reasoning({ r }: { r: AnalysisResult }) {
  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader eyebrow="Technical findings" title="What the analysts saw" />
        {r.technicalFindings.length === 0 ? (
          <div className="px-6 pb-6 font-mono text-xs text-ink/50">No technical findings recorded.</div>
        ) : (
          <ul className="px-6 pb-6 space-y-2.5 text-sm text-ink/80">
            {r.technicalFindings.map((f, i) => (
              <li key={i} className="flex items-start gap-3"><span className="mt-2 w-1.5 h-1.5 rounded-full bg-ink shrink-0" />{f}</li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel variant="ink">
        <PanelHeader eyebrow={<span className="text-bone/60">Band case room</span>} title={<span className="text-bone">Multi-agent investigation</span>} />
        <div className="px-6 pb-6 font-mono text-xs text-bone/70 leading-relaxed">
          The eight PARALLAX agents debate this evidence bundle live in a Band room — intake, device-compromise,
          transaction-trace, mule-graph, evidence-validator, liability, legal-evidence, and the decision convenor —
          and converge on an action packet. The transcript streams in the Band workspace, not the static report.
        </div>
      </Panel>
    </div>
  );
}

// ---------------- Evidence ----------------
const ARTIFACTS: { name: string; label: string }[] = [
  { name: "report.html", label: "Report · HTML" },
  { name: "report.pdf", label: "Report · PDF" },
  { name: "stix", label: "STIX 2.1 bundle" },
  { name: "yara", label: "YARA rule" },
  { name: "fraud-rules", label: "Fraud rules" },
];

function Evidence({ sub, r }: { sub: Submission; r: AnalysisResult }) {
  const guard = useDemoGuard();
  const [quarantine, setQuarantine] = useState<string | null>(null);
  const [qErr, setQErr] = useState<string | null>(null);
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-7 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Indicators of compromise" title={`${r.iocs.length} extracted`} />
          {r.iocs.length === 0 ? (
            <div className="px-6 pb-5 font-mono text-xs text-ink/50">No IOCs extracted.</div>
          ) : (
            <div className="px-6 pb-5 space-y-2">
              {r.iocs.map((io, i) => (
                <div key={i} className="flex items-center justify-between gap-3 font-mono text-xs">
                  <Pill tone="muted">{io.type}</Pill>
                  <CopyableText text={io.value} className="flex-1 min-w-0 truncate text-right" />
                </div>
              ))}
            </div>
          )}
        </Panel>
        {r.riskNotes.length > 0 && (
          <Panel>
            <PanelHeader eyebrow="Scoring notes" title="Auditable adjustments" />
            <ul className="px-6 pb-5 space-y-1.5 font-mono text-[11px] text-ink/70">
              {r.riskNotes.map((n, i) => <li key={i}>· {n}</li>)}
            </ul>
          </Panel>
        )}
      </div>
      <div className="col-span-12 lg:col-span-5 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Downloads" title="Delivery artifacts" />
          <div className="px-6 pb-5 space-y-2">
            {ARTIFACTS.map((a) => (
              <button
                key={a.name}
                onClick={() => guard(`Downloading ${a.label}`) && window.open(artifactUrl(sub.id, a.name), "_blank")}
                className="btn w-full justify-between h-10 px-3 text-xs"
              >
                <span>{a.label}</span><Download className="w-3.5 h-3.5" />
              </button>
            ))}
          </div>
        </Panel>
        <Panel variant="ink">
          <PanelHeader eyebrow={<span className="text-bone/60">Quarantined sample</span>} title={<span className="text-bone">Signed APK access</span>} />
          <div className="px-6 pb-6 space-y-2 font-mono text-xs text-bone/70">
            <p>The raw APK lives in a quarantine bucket. Request a short-lived signed URL — it is never executed on the API host.</p>
            <button
              onClick={async () => { if (!guard("Generating a signed APK URL")) return; setQErr(null); try { setQuarantine((await quarantineUrl(sub.id)).url); } catch (e) { setQErr(e instanceof Error ? e.message : "Failed"); } }}
              className="h-10 px-3 w-full border border-bone/40 text-bone hover:bg-bone hover:text-ink transition-colors flex items-center justify-center gap-2"
            >
              Generate signed URL
            </button>
            {quarantine && <a href={quarantine} target="_blank" rel="noreferrer" className="block truncate text-acid underline">{quarantine}</a>}
            {qErr && <div className="text-oxblood">{qErr}</div>}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function GraphView({ taig, loading }: { taig: TAIGNodes | null; loading: boolean }) {
  if (loading) return <CenterState><Loader2 className="w-4 h-4 animate-spin" /> Building graph…</CenterState>;
  if (!taig || taig.nodes.length === 0) return <Panel><div className="px-6 py-16 text-center font-mono text-xs text-ink/50">No graph data.</div></Panel>;
  return (
    <Panel>
      <PanelHeader eyebrow="TAIG" title="Threat-Annotated Instruction Graph" right={<span className="font-mono text-[10px] text-ink/50">{taig.nodes.length} nodes · {taig.edges.length} edges</span>} />
      <div className="p-4"><TAIGGraph nodes={taig.nodes} edges={taig.edges} height={520} /></div>
    </Panel>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 min-w-0">
      <span className="text-ink/50 shrink-0">{label}</span>
      {children}
    </div>
  );
}
