/**
 * PARALLAX API client — speaks the real backend contract and degrades safely.
 *
 * Live backend (FastAPI, see parallax/api):
 *   POST /api/v1/analyze                         multipart APK submit (X-API-Key)
 *   GET  /api/v1/history?page=&page_size=        paginated submissions
 *   GET  /api/v1/history/stream                  SSE live submission list
 *   GET  /api/v1/analysis/{id}                   single submission
 *   GET  /api/v1/analysis/{id}/stream            SSE live status for one submission
 *   GET  /api/v1/analysis/{id}/result            cortex_result + fraud_chain
 *   GET  /api/v1/analysis/{id}/{artifact}        report.html|report.pdf|stix|yara|fraud-rules
 *   GET  /api/v1/analysis/{id}/quarantine-url    signed APK URL
 *   POST /api/v1/hunt   ·  GET /api/v1/hunt/templates
 *   GET  /api/v1/graph/health   ·   GET /health
 *
 * Auth: the analyst's key (from the auth session) is sent as `X-API-Key`, and as
 * `?api_key=` on EventSource/download URLs that can't set headers.
 *
 * Failsafe: `?demo=true` or a `demo-` key forces seeded data. Otherwise calls go
 * live; callers use `useAsync` to render loading/error/empty states rather than
 * white-screening. Backend snake_case + 0-100 scores are mapped to the view model.
 */

import * as mock from "./mock-data";

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ||
  "/api/v1";

const KEY_STORAGE = "parallax.sessionKey";

export function getKey(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(KEY_STORAGE);
}

export function isDemo(): boolean {
  if (typeof window === "undefined") return true;
  const p = new URLSearchParams(window.location.search);
  if (p.get("demo") === "true" || p.get("demo") === "1") return true;
  const k = getKey();
  return !!k && k.startsWith("demo-");
}

// ----------------------------------------------------------------- view model
export type Verdict = "CLEAN" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Status = "queued" | "running" | "complete" | "failed";

export interface Submission {
  id: string;
  packageName: string;
  fileName: string;
  sizeBytes: number;
  sha256: string;
  submittedAt: string;
  submittedBy?: string;
  status: Status;
  stage: string; // real backend stage: triaging | static | dynamic | reasoning | …
  verdict?: Verdict;
  riskScore: number; // 0-100 (calibrated)
  family?: string;
  permissions: string[];
  iocs: number;
  durationMs: number;
  tags: string[];
}

export interface AnalysisResult {
  executiveSummary: string;
  technicalFindings: string[];
  attck: string[];
  iocs: { type: string; value: string }[];
  recommendations: { action: string; rationale: string; mode: string }[];
  irt: { status: string; claim: string; explanation: string }[];
  components: Record<string, number>;
  weights: Record<string, number>;
  evidenceScore: number;
  calibratedScore: number;
  confidence: { score: number; band: string; needsReview: boolean; drivers: string[] } | null;
  family?: string;
  familyConfidence?: number;
  riskNotes: string[];
  raw: Record<string, unknown>;
}

export interface ThreatHuntHit {
  id: string;
  indicator: string;
  type: string;
  matchedIn: string;
  firstSeen: string;
  severity: "low" | "medium" | "high" | "critical";
  family: string;
}

export interface TAIGNodes {
  nodes: Array<{ id: string; label: string; type: "class" | "method" | "string" | "permission" | "ioc" }>;
  edges: Array<{ from: string; to: string; relationship: string }>;
}

export interface RecentEvent {
  time: string;
  text: string;
  kind: "danger" | "warn" | "ok" | "info";
}

export interface KpiResponse {
  totalSubmissions: number;
  activeThreats: number;
  criticalRisk: number;
  avgRiskScore: number;
  familiesIdentified: number;
  familiesTracked: number;
  newFamilies: number;
  iocsDiscovered: number;
  trend: number[];
}

// ----------------------------------------------------------------- transport
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function headers(): HeadersInit {
  const h: Record<string, string> = { Accept: "application/json" };
  const k = getKey();
  if (k) h["X-API-Key"] = k;
  return h;
}

async function live<T>(path: string, init: RequestInit = {}): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...headers(), ...(init.headers || {}) } });
  } catch (e) {
    throw new ApiError(0, `Cannot reach the PARALLAX API at ${API_BASE}. Is the backend running?`);
  }
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const body = await r.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(r.status, detail);
  }
  return (await r.json()) as T;
}

/** Build an authed URL for EventSource / artifact downloads (header-less). */
export function authedUrl(path: string): string {
  const k = getKey();
  const sep = path.includes("?") ? "&" : "?";
  return `${API_BASE}${path}${k ? `${sep}api_key=${encodeURIComponent(k)}` : ""}`;
}

// ----------------------------------------------------------------- mappers
const TERMINAL = new Set(["complete", "failed"]);

function mapStatus(s: string | undefined): Status {
  if (s === "complete") return "complete";
  if (s === "failed") return "failed";
  if (s === "queued") return "queued";
  return "running";
}

function normVerdict(v: string | undefined | null): Verdict | undefined {
  if (!v) return undefined;
  const u = v.toUpperCase();
  if (["CLEAN", "LOW", "MEDIUM", "HIGH", "CRITICAL"].includes(u)) return u as Verdict;
  if (u === "SUSPICIOUS") return "MEDIUM";
  if (u === "MALICIOUS") return "HIGH";
  return undefined;
}

interface RawSubmission {
  id: string;
  sha256?: string;
  file_name?: string;
  file_size?: number;
  package_name?: string | null;
  status?: string;
  verdict?: string | null;
  final_score?: number | null;
  triage_score?: number | null;
  created_at?: string;
  updated_at?: string;
  metadata?: Record<string, any> | null;
  metadata_json?: Record<string, any> | null;
}

function mapSubmission(r: RawSubmission): Submission {
  const meta = r.metadata || r.metadata_json || {};
  const cortex = meta.cortex_result || {};
  const intel = cortex.intel_correlator || {};
  const features = (meta.re_workbench_artifact?.static_features || meta.static_features || {}) as Record<string, any>;
  const created = r.created_at ? new Date(r.created_at).getTime() : Date.now();
  const updated = r.updated_at ? new Date(r.updated_at).getTime() : created;
  const score = r.final_score ?? r.triage_score ?? 0;
  const iocList = cortex.iocs || {};
  const iocCount =
    (iocList.domains?.length || 0) + (iocList.ips?.length || 0) + (iocList.urls?.length || 0);
  const tags = [cortex.code_interpreter?.intent_classification, intel.family_attribution]
    .filter((t: unknown): t is string => typeof t === "string" && t !== "uncertain");
  return {
    id: String(r.id),
    packageName: r.package_name || r.file_name || "unknown.apk",
    fileName: r.file_name || "unknown.apk",
    sizeBytes: r.file_size || 0,
    sha256: r.sha256 || "",
    submittedAt: r.created_at || new Date().toISOString(),
    status: mapStatus(r.status),
    stage: r.status || "queued",
    verdict: normVerdict(r.verdict),
    riskScore: Math.round((score as number) * 10) / 10,
    family: intel.family_attribution || undefined,
    permissions: Array.isArray(features.permissions) ? features.permissions : [],
    iocs: iocCount,
    durationMs: Math.max(0, updated - created),
    tags: Array.from(new Set(tags)),
  };
}

// ----------------------------------------------------------------- failsafe wrap
async function withDemo<T>(liveFn: () => Promise<T>, demoVal: () => T): Promise<T> {
  if (isDemo()) return demoVal();
  return liveFn();
}

// ----------------------------------------------------------------- endpoints
export interface SubmissionsListResponse {
  items: Submission[];
  total: number;
  page: number;
  pageSize: number;
}

export async function getSubmissions(page = 1, pageSize = 20): Promise<SubmissionsListResponse> {
  return withDemo(
    async () => {
      const raw = await live<{ items: RawSubmission[]; total: number; page: number; page_size: number }>(
        `/history?page=${page}&page_size=${pageSize}`
      );
      return {
        items: (raw.items || []).map(mapSubmission),
        total: raw.total ?? raw.items?.length ?? 0,
        page: raw.page ?? page,
        pageSize: raw.page_size ?? pageSize,
      };
    },
    () => {
      const start = (page - 1) * pageSize;
      return { items: mock.submissions.slice(start, start + pageSize), total: mock.submissions.length, page, pageSize };
    }
  );
}

export async function getSubmission(id: string): Promise<Submission> {
  return withDemo(
    async () => mapSubmission(await live<RawSubmission>(`/analysis/${id}`)),
    () => {
      const s = mock.submissions.find((s) => s.id === id);
      if (!s) throw new ApiError(404, `Submission ${id} not found`);
      return s;
    }
  );
}

export async function getResult(id: string): Promise<AnalysisResult> {
  return withDemo(
    async () => mapResult(await live<Record<string, any>>(`/analysis/${id}/result`)),
    () => mock.mockResult(id)
  );
}

function mapResult(raw: Record<string, any>): AnalysisResult {
  const cortex = raw.cortex_result || raw || {};
  const risk = cortex.risk || {};
  const intel = cortex.intel_correlator || {};
  const iocs = cortex.iocs || {};
  const flat: { type: string; value: string }[] = [];
  for (const t of ["domains", "ips", "urls"] as const) {
    for (const v of iocs[t] || []) flat.push({ type: t.slice(0, -1), value: v });
  }
  const conf = cortex.confidence;
  return {
    executiveSummary: cortex.executive_summary || "",
    technicalFindings: cortex.technical_findings || [],
    attck: cortex.attck_techniques || [],
    iocs: flat,
    recommendations: (cortex.recommendations || []).map((r: any) => ({
      action: r.action || "",
      rationale: r.rationale || "",
      mode: r.approval_mode || "SUGGEST",
    })),
    irt: (cortex.irt || []).map((e: any) => ({
      status: e.status || "CONFIRMED",
      claim: e.claim || "",
      explanation: e.explanation || "",
    })),
    components: risk.components || {},
    weights: risk.weights || {},
    evidenceScore: risk.evidence_score ?? 0,
    calibratedScore: risk.calibrated_score ?? 0,
    confidence: conf
      ? { score: conf.score ?? 0, band: conf.band ?? "low", needsReview: !!conf.needs_human_review, drivers: conf.drivers || [] }
      : null,
    family: intel.family_attribution || undefined,
    familyConfidence: intel.family_confidence ?? undefined,
    riskNotes: risk.notes || [],
    raw: cortex,
  };
}

export interface SubmitResult {
  id: string;
  status: string;
}

export async function submitApk(file: File, opts: { webhookUrl?: string } = {}): Promise<SubmitResult> {
  if (isDemo()) {
    await new Promise((r) => setTimeout(r, 700));
    return { id: mock.submissions[0]?.id ?? "demo", status: "queued" };
  }
  const fd = new FormData();
  fd.append("file", file);
  if (opts.webhookUrl) fd.append("webhook_url", opts.webhookUrl);
  const raw = await live<RawSubmission>(`/analyze`, { method: "POST", body: fd });
  return { id: String(raw.id), status: raw.status || "queued" };
}

export async function getKpi(): Promise<KpiResponse> {
  return withDemo(
    async () => {
      // The backend has no /kpi; derive a real summary from the submission feed.
      const { items, total } = await getSubmissions(1, 100);
      const scored = items.filter((s) => s.riskScore > 0);
      const families = new Set(items.map((s) => s.family).filter(Boolean) as string[]);
      const iocs = items.reduce((a, s) => a + s.iocs, 0);
      return {
        totalSubmissions: total,
        activeThreats: items.filter((s) => s.verdict === "HIGH" || s.verdict === "CRITICAL").length,
        criticalRisk: items.filter((s) => s.verdict === "CRITICAL").length,
        avgRiskScore: scored.length ? scored.reduce((a, s) => a + s.riskScore, 0) / scored.length : 0,
        familiesIdentified: families.size,
        familiesTracked: families.size,
        newFamilies: 0,
        iocsDiscovered: iocs,
        trend: [],
      };
    },
    () => mock.kpiSummary
  );
}

export interface HuntResponse {
  hits: ThreatHuntHit[];
  total: number;
}

export async function threatHunt(q: string): Promise<HuntResponse> {
  return withDemo(
    async () => {
      const body = { hunt: "high_risk_apks", sha256: q, family: q, technique: q, value: q, min_score: 60, limit: 50 };
      const raw = await live<{ results?: any[]; hits?: any[] }>(`/hunt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const rows = raw.results || raw.hits || [];
      const hits: ThreatHuntHit[] = rows.map((r: any, i: number) => ({
        id: String(r.id ?? i),
        indicator: r.value || r.indicator || r.sha256 || r.domain || r.ip || "—",
        type: r.ioc_type || r.type || "indicator",
        matchedIn: r.sha256 || r.submission_id || r.matched_in || "—",
        firstSeen: r.created_at || r.first_seen || new Date().toISOString(),
        severity: (r.severity || (r.score >= 80 ? "critical" : r.score >= 60 ? "high" : "medium")) as ThreatHuntHit["severity"],
        family: r.family || r.family_attribution || "—",
      }));
      return { hits, total: hits.length };
    },
    () => {
      const ql = q.toLowerCase();
      const hits = ql
        ? mock.threatHuntHits.filter(
            (h) => h.indicator.toLowerCase().includes(ql) || h.family.toLowerCase().includes(ql) || h.type.includes(ql)
          )
        : mock.threatHuntHits;
      return { hits, total: hits.length };
    }
  );
}

/** Per-submission TAIG view. The live graph lives in Neo4j (no REST node/edge
 *  feed), so we derive a faithful local graph from the analysis result. */
export async function getTAIGGraph(submissionId: string): Promise<TAIGNodes> {
  return withDemo(
    async () => {
      try {
        const res = await getResult(submissionId);
        return buildGraphFromResult(submissionId, res);
      } catch {
        return mock.taigGraph;
      }
    },
    () => mock.taigGraph
  );
}

function buildGraphFromResult(pkg: string, res: AnalysisResult): TAIGNodes {
  const nodes: TAIGNodes["nodes"] = [{ id: "pkg", label: res.family || "submission", type: "class" }];
  const edges: TAIGNodes["edges"] = [];
  res.iocs.slice(0, 10).forEach((io, i) => {
    const id = `ioc${i}`;
    nodes.push({ id, label: io.value, type: "ioc" });
    edges.push({ from: "pkg", to: id, relationship: "communicates" });
  });
  res.attck.slice(0, 10).forEach((t, i) => {
    const id = `att${i}`;
    nodes.push({ id, label: t, type: "method" });
    edges.push({ from: "pkg", to: id, relationship: "exhibits" });
  });
  if (nodes.length === 1) return mock.taigGraph;
  return { nodes, edges };
}

export function artifactUrl(id: string, artifact: string): string {
  return authedUrl(`/analysis/${id}/${artifact}`);
}

export async function quarantineUrl(id: string): Promise<{ url: string; expiresInSeconds: number }> {
  const raw = await live<{ url: string; expires_in_seconds?: number }>(`/analysis/${id}/quarantine-url`);
  return { url: raw.url, expiresInSeconds: raw.expires_in_seconds ?? 300 };
}

// ----------------------------------------------------------------- SSE
/** Subscribe to live submission-list updates. Returns an unsubscribe fn.
 *  No-op in demo mode. */
export function streamHistory(onItems: (items: Submission[]) => void): () => void {
  if (isDemo() || typeof EventSource === "undefined") return () => {};
  const es = new EventSource(authedUrl(`/history/stream`));
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (Array.isArray(data.items)) onItems(data.items.map(mapSubmission));
    } catch {
      /* ignore malformed frame */
    }
  };
  es.onerror = () => es.close();
  return () => es.close();
}

export function streamAnalysis(id: string, onUpdate: (sub: Submission) => void): () => void {
  if (isDemo() || typeof EventSource === "undefined") return () => {};
  const es = new EventSource(authedUrl(`/analysis/${id}/stream`));
  es.onmessage = (e) => {
    try {
      onUpdate(mapSubmission(JSON.parse(e.data)));
    } catch {
      /* ignore */
    }
  };
  es.onerror = () => es.close();
  return () => es.close();
}

export async function getRecentEvents(): Promise<RecentEvent[]> {
  return withDemo(
    async () => {
      const { items } = await getSubmissions(1, 12);
      return items.map((s) => ({
        time: relAgo(s.submittedAt),
        text: `${s.packageName} — ${s.verdict ?? s.stage}${s.family ? ` · ${s.family}` : ""}${
          s.riskScore ? ` · ${s.riskScore.toFixed(0)}/100` : ""
        }`,
        kind: s.verdict === "CRITICAL" || s.verdict === "HIGH" ? "danger" : s.status === "complete" ? "ok" : "info",
      }));
    },
    () => mock.recentEvents
  );
}

export async function getRecentFamilies(): Promise<typeof mock.recentFamilies> {
  return withDemo(
    async () => {
      const { items } = await getSubmissions(1, 100);
      const counts = new Map<string, number>();
      for (const s of items) if (s.family) counts.set(s.family, (counts.get(s.family) || 0) + 1);
      const rows = [...counts.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([family, count]) => ({ family, count, delta: 0, trend: "flat" as const }));
      return rows.length ? rows : mock.recentFamilies;
    },
    () => mock.recentFamilies
  );
}

function relAgo(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}
