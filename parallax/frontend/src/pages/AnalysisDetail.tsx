import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  Boxes,
  Brain,
  Check,
  Copy,
  Database,
  Download,
  ExternalLink,
  Eye,
  FileText,
  Hash,
  KeyRound,
  Layers,
  Microscope,
  Network,
  Package,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Kpi } from "../components/primitives/Kpi";
import { Pill, VerdictPill } from "../components/primitives/Pill";
import { CopyableText, JsonView } from "../components/primitives/JsonView";
import { TAIGGraph, Distribution } from "../components/primitives/Graph";
import { getSubmission, getTAIGGraph } from "../lib/api";
import { type Submission, type TAIGNodes } from "../lib/mock-data";
import { cn, dur, fmt, pct, relTime, riskColor, shortHash } from "../lib/utils";

type Tab = "overview" | "static" | "dynamic" | "reasoning" | "evidence" | "graph";

export default function AnalysisDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [sub, setSub] = useState<Submission | null>(null);
  const [taig, setTaig] = useState<TAIGNodes | null>(null);
  const [tab, setTab] = useState<Tab>("overview");

  useEffect(() => {
    void (async () => {
      try {
        const s = await getSubmission(id);
        setSub(s);
        const g = await getTAIGGraph(id);
        setTaig(g);
      } catch (e) {
        navigate("/console");
      }
    })();
  }, [id, navigate]);

  if (!sub) return <Loading />;

  return (
    <div>
      <Topbar
        eyebrow={
          <span className="flex items-center gap-2">
            <Link to="/console" className="hover:text-ink">Submissions</Link>
            <span>/</span>
            <span>{sub.id}</span>
          </span> as unknown as string
        }
        title={sub.packageName}
        right={
          <>
            <Link to={`/graph?from=${sub.id}`} className="btn h-9 px-3 text-xs">
              <Network className="w-3.5 h-3.5" />
              TAIG
            </Link>
            <button className="btn h-9 px-3 text-xs">
              <Download className="w-3.5 h-3.5" />
              Bundle
            </button>
          </>
        }
      >
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            {sub.verdict && <VerdictPill verdict={sub.verdict} pulse={sub.status === "running"} />}
            {sub.family && <Pill tone="oxblood">{sub.family}</Pill>}
            {sub.tags.map((t) => (
              <Pill key={t} tone="bone">{t}</Pill>
            ))}
            <span className="font-mono text-[10px] text-ink/50">· {relTime(sub.submittedAt)}</span>
          </div>
          <div className="font-mono text-[10px] text-ink/50">
            {sub.fileName} · {(sub.sizeBytes / 1024 / 1024).toFixed(2)} MB
          </div>
        </div>
      </Topbar>

      <div className="p-6 max-w-[1600px]">
        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-px bg-ink/20 border border-ink/10 mb-6">
          <Kpi
            eyebrow="Risk score"
            value={sub.riskScore}
            formatter={(n) => n.toFixed(1)}
            unit="/ 10"
            emphasis={riskColor(sub.riskScore) === "danger" ? ("oxblood" as const) : "bone"}
          />
          <Kpi eyebrow="Verdict" value={sub.verdict ?? "PENDING"} emphasis="bone" />
          <Kpi eyebrow="IOCs found" value={sub.iocs} emphasis="bone" />
          <Kpi eyebrow="Duration" value={dur(sub.durationMs)} emphasis="bone" />
          <Kpi eyebrow="Threat-hunt hits" value={sub.threatHuntHits} emphasis="bone" />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-px bg-ink/20 border border-ink/10 mb-6">
          {(["overview", "static", "dynamic", "reasoning", "evidence", "graph"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "h-10 px-5 font-mono text-[10px] uppercase tracking-widest transition-colors",
                tab === t ? "bg-ink text-bone" : "bg-bone-50 text-ink/60 hover:text-ink"
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "overview" && <Overview sub={sub} />}
        {tab === "static" && <Static sub={sub} />}
        {tab === "dynamic" && <Dynamic sub={sub} />}
        {tab === "reasoning" && <Reasoning />}
        {tab === "evidence" && <Evidence sub={sub} />}
        {tab === "graph" && <GraphView taig={taig} />}
      </div>
    </div>
  );
}

function Loading() {
  return (
    <div className="h-full flex items-center justify-center min-h-[60vh]">
      <div className="font-mono text-xs uppercase tracking-widest text-ink/40 animate-pulse">Loading…</div>
    </div>
  );
}

// =============== Tab: Overview ===============
function Overview({ sub }: { sub: Submission }) {
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-8 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Summary" title="What happened" />
          <div className="px-6 pb-6 font-sans text-sm leading-relaxed text-ink/80">
            <p>
              <strong className="font-display text-xl text-ink">{sub.packageName}</strong> was submitted
              {relTime(sub.submittedAt)}. Static analysis identified the package as
              {" "}
              <span className="text-oxblood font-medium">
                {sub.family ?? "unclassified"}
              </span>{" "}
              with a {sub.riskScore.toFixed(1)}/10 risk score.
            </p>
            <p className="mt-4">
              {sub.iocs} indicators of compromise were extracted and cross-referenced against the threat
              hunt index. {sub.threatHuntHits} matches were found. The case room was opened with the
              multi-agent panel, which reached consensus on the verdict in 6 rounds of debate.
            </p>
          </div>
        </Panel>

        <Panel>
          <PanelHeader eyebrow="Why this verdict" title="Reasoning chain" />
          <ul className="px-6 pb-6 space-y-3">
            {[
              { who: "Static Analyst", what: "BIND_ACCESSIBILITY_SERVICE + RECEIVE_SMS + SEND_SMS — strong SMS-stealer pattern", kind: "evidence" },
              { who: "Dynamic Hunter", what: "Frida hook on SmsManager.sendTextMessage captured 3 sends to premium numbers", kind: "evidence" },
              { who: "Reasoning Agent", what: "DexClassLoader usage + dynamic payload fetch → dropper, not direct malware", kind: "claim" },
              { who: "Evidence Validator", what: "Verified all 3 SMS sends traced to com.sec.sharkbot (not a library), reject null hypothesis", kind: "challenge" },
              { who: "Decision Convenor", what: "Verdict locked at CRITICAL 9.2 — consensus reached", kind: "verdict" },
            ].map((r, i) => (
              <li key={i} className="flex items-start gap-3 font-mono text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-ink mt-2 shrink-0" />
                <div>
                  <span className="text-ink font-medium">{r.who}:</span>{" "}
                  <span className="text-ink/70">{r.what}</span>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="col-span-12 lg:col-span-4 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Hashes" title="Identity" />
          <div className="px-6 pb-5 space-y-3 font-mono text-xs">
            <HashRow label="SHA-256" value={sub.sha256} />
            <HashRow label="Size" value={`${(sub.sizeBytes / 1024 / 1024).toFixed(2)} MB`} />
            <HashRow label="Submitted by" value={sub.submittedBy} />
            <HashRow label="Submission ID" value={sub.id} />
          </div>
        </Panel>

        <Panel variant="ink">
          <PanelHeader
            eyebrow={<span className="text-bone/60">Recommended action</span>}
            title={<span className="text-bone">Block & investigate</span>}
          />
          <div className="px-6 pb-6 space-y-2 font-mono text-xs text-bone/80">
            <Action>Block package from production store</Action>
            <Action>Add {sub.family} family to threat-hunt feed</Action>
            <Action>Quarantine device for 24h observation</Action>
            <Action>Notify SOC within 4h SLA</Action>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function HashRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2 min-w-0">
      <span className="text-ink/50 shrink-0">{label}</span>
      <CopyableText text={value} className="min-w-0 truncate" />
    </div>
  );
}

function Action({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <Check className="w-3.5 h-3.5 text-acid shrink-0" strokeWidth={2.2} />
      <span>{children}</span>
    </div>
  );
}

// =============== Tab: Static ===============
function Static({ sub }: { sub: Submission }) {
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-6">
        <Panel>
          <PanelHeader eyebrow="Decompiled" title="Manifest & key classes" />
          <div className="px-6 pb-5 font-mono text-xs">
            <JsonView
              data={{
                package: sub.packageName,
                minSdk: 24,
                targetSdk: 33,
                permissions: sub.permissions,
                activities: ["MainActivity", "C2Service", "SmsReceiver"],
                services: ["AccessibilityService", "BootReceiver"],
                signature_valid: false,
                signed_with_debug_key: true,
                repackaged: true,
              }}
            />
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-6 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Permissions" title={`${sub.permissions.length} declared`} />
          <ul className="px-6 pb-5 space-y-1.5 font-mono text-xs">
            {sub.permissions.map((p) => (
              <li key={p} className="flex items-center justify-between gap-2">
                <span className="text-ink/80">{p}</span>
                {isDangerous(p) && <Pill tone="danger">abuse</Pill>}
              </li>
            ))}
          </ul>
        </Panel>
        <Panel>
          <PanelHeader eyebrow="Suspicious API calls" title="Detected" />
          <div className="px-6 pb-5 space-y-2 font-mono text-xs">
            {[
              { api: "SmsManager.sendTextMessage", count: 3 },
              { api: "DexClassLoader.<init>", count: 2 },
              { api: "Runtime.exec", count: 1 },
              { api: "Cipher.doFinal", count: 14 },
              { api: "AccessibilityService.onAccessibilityEvent", count: 27 },
            ].map((row) => (
              <div key={row.api} className="flex items-center justify-between gap-2">
                <span className="text-ink/80">{row.api}</span>
                <span className="text-ink/50">×{row.count}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function isDangerous(perm: string): boolean {
  return [
    "RECEIVE_SMS",
    "SEND_SMS",
    "READ_SMS",
    "BIND_ACCESSIBILITY_SERVICE",
    "SYSTEM_ALERT_WINDOW",
    "BIND_DEVICE_ADMIN",
    "REQUEST_INSTALL_PACKAGES",
  ].includes(perm);
}

// =============== Tab: Dynamic ===============
function Dynamic({ sub }: { sub: Submission }) {
  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader eyebrow="Frida runtime" title="Hooked APIs" />
        <div className="px-6 pb-5 space-y-3">
          {[
            { hook: "android.telephony.SmsManager.sendTextMessage", calls: 3, captured: 3, threat: "critical" as const },
            { hook: "dalvik.system.DexClassLoader.<init>", calls: 2, captured: 2, threat: "high" as const },
            { hook: "android.app.AccessibilityService.onAccessibilityEvent", calls: 27, captured: 5, threat: "high" as const },
            { hook: "javax.crypto.Cipher.doFinal", calls: 14, captured: 3, threat: "medium" as const },
          ].map((h) => (
            <div key={h.hook} className="border border-ink/10 p-3 flex items-center gap-4">
              <div className="font-mono text-xs text-ink flex-1 truncate">{h.hook}</div>
              <Pill tone={h.threat === "critical" ? "danger" : h.threat === "high" ? "warn" : "muted"}>
                {h.threat}
              </Pill>
              <div className="font-mono text-[10px] text-ink/60 shrink-0">
                {h.captured} / {h.calls} captured
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel>
        <PanelHeader eyebrow="Captured call" title="Sample observation" />
        <div className="px-6 pb-5">
          <JsonView
            data={{
              type: "observation",
              schema_version: "1.0",
              hypothesis_id: "HYP-SMS-001",
              hook: "android.telephony.SmsManager.sendTextMessage",
              captured_at_ms: Date.now() - 5 * 60 * 1000,
              thread_id: 14,
              thread_name: "pool-3-thread-1",
              caller_package: sub.packageName,
              args: {
                destination: "+15551234567",
                text: "VERIFY 84H2",
              },
              return_value: null,
              exception: null,
              session_id: "sess_3f9b…",
            }}
          />
        </div>
      </Panel>
    </div>
  );
}

// =============== Tab: Reasoning ===============
function Reasoning() {
  return (
    <Panel>
      <PanelHeader eyebrow="Case room CR-2401" title="Multi-agent transcript" />
      <div className="px-6 pb-6 space-y-4">
        {[
          { agent: "IntakeAgent", text: "Opening case for sub_0001 (SharkBot suspected). Family score 0.91 from static embedder." },
          { agent: "StaticAnalyst", text: "Confirming: BIND_ACCESSIBILITY_SERVICE + SMS triad. Permissions cross-referenced with SharkBot TTP pattern (T1660)." },
          { agent: "DynamicHunter", text: "Hooked SmsManager.sendTextMessage. Captured 3 sends to premium numbers, all from com.sec.sharkbot thread pool-3." },
          { agent: "ReasoningAgent", text: "Claim: dropper. Evidence: dynamic payload fetch from evil-cdn.duckdns.org at boot. Risk 9.2." },
          { agent: "EvidenceValidator", text: "Challenge @ReasoningAgent — verify that the 3 SMS sends trace to the package, not a library. … Verified, all 3 are direct calls from com.sec.sharkbot. Stand." },
          { agent: "DecisionConvenor", text: "Consensus: CRITICAL 9.2. Locking verdict. Evidence bundle dispatched." },
        ].map((m, i) => (
          <div key={i} className="flex gap-3">
            <div className="w-8 h-8 bg-ink text-bone flex items-center justify-center font-display text-sm shrink-0">
              {m.agent[0]}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-widest text-ink/50 mb-1">
                {m.agent}
              </div>
              <div className="text-sm text-ink/80 leading-relaxed">{m.text}</div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// =============== Tab: Evidence ===============
function Evidence({ sub }: { sub: Submission }) {
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-8">
        <Panel>
          <PanelHeader eyebrow="Evidence bundle" title="Signed" />
          <div className="px-6 pb-5 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-ink/50">Bundle SHA-256</span>
              <CopyableText text="a3f9b2e1c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink/50">Signature</span>
              <CopyableText text="MEUCIQCx1234…" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink/50">S3 location</span>
              <CopyableText text="s3://parallax-evidence/2026/06/sub_0001.tar.gz" />
            </div>
            <div className="rule" />
            <div>
              <div className="eyebrow mb-2">Bundle contents</div>
              <JsonView
                data={{
                  "manifest.json": "8.2 kB",
                  "static_report.json": "124 kB",
                  "decompiled/": "12 MB",
                  "screenshots/": "2.4 MB",
                  "frida/observations.jsonl": "47 kB",
                  "frida/payload.js": "3.1 kB",
                  "taig_graph.json": "8.7 kB",
                  "model_run.json": "12 kB",
                  "report.pdf": "962 kB",
                }}
              />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4 space-y-6">
        <Panel>
          <PanelHeader eyebrow="Hooks executed" title="4 of 14" />
          <div className="px-6 pb-5">
            <Distribution
              items={[
                { label: "SmsManager", value: 3, color: "#7C1F2D" },
                { label: "DexClassLoader", value: 2, color: "#7C1F2D" },
                { label: "Accessibility", value: 5, color: "#C9923A" },
                { label: "Cipher.doFinal", value: 3, color: "#C9923A" },
                { label: "Runtime.exec", value: 1, color: "#7C1F2D" },
              ]}
            />
          </div>
        </Panel>
        <Panel variant="ink">
          <PanelHeader
            eyebrow={<span className="text-bone/60">Cost</span>}
            title={<span className="text-bone">$0.18</span>}
          />
          <div className="px-6 pb-6 space-y-2 font-mono text-xs text-bone/80">
            <CostRow label="Static" cost="$0.012" />
            <CostRow label="Dynamic" cost="$0.041" />
            <CostRow label="Reasoning" cost="$0.118" />
            <CostRow label="Delivery" cost="$0.009" />
            <div className="rule bg-bone/20" />
            <CostRow label="Total" cost="$0.180" highlight />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function CostRow({ label, cost, highlight = false }: { label: string; cost: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className={cn("text-bone/70", highlight && "text-bone")}>{label}</span>
      <span className={cn("tabular-nums", highlight ? "text-bone font-medium" : "text-bone/80")}>{cost}</span>
    </div>
  );
}

// =============== Tab: Graph ===============
function GraphView({ taig }: { taig: TAIGNodes | null }) {
  if (!taig) return <div className="font-mono text-xs text-ink/50">Loading graph…</div>;
  return (
    <Panel>
      <PanelHeader
        eyebrow="TAIG"
        title="Threat-Annotated Instruction Graph"
        right={
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-ink/50">
            <span>{taig.nodes.length} nodes</span>
            <span>·</span>
            <span>{taig.edges.length} edges</span>
          </div>
        }
      />
      <div className="p-4">
        <TAIGGraph nodes={taig.nodes} edges={taig.edges} height={520} />
      </div>
    </Panel>
  );
}
