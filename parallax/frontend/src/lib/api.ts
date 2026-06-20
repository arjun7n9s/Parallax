/**
 * API client. When `?demo=true` is in the URL (or the configured VITE_API_BASE
 * returns 404 on a health check), all calls return mock data so the UI is
 * fully interactive without a live backend.
 *
 * The live backend contract is:
 *   GET  /api/v1/history?page=&page_size=     -> paginated submissions
 *   GET  /api/v1/submissions/{id}            -> single submission detail
 *   POST /api/v1/analyze                     -> submit an APK
 *   GET  /api/v1/threat-hunt?q=              -> threat hunt results
 *   GET  /api/v1/kpi                         -> aggregate KPIs
 *   GET  /health                             -> 200 if alive
 */

import * as mock from "./mock-data";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) || "/api/v1";
const DEMO_PARAM = "demo";

export const isDemo = (): boolean => {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  return params.get(DEMO_PARAM) === "true" || params.get(DEMO_PARAM) === "1";
};

interface ApiOptions {
  signal?: AbortSignal;
}

async function live<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    signal: opts.signal,
  });
  if (!r.ok) {
    throw new Error(`API ${r.status} ${r.statusText} on ${path}`);
  }
  return (await r.json()) as T;
}

export interface KpiResponse {
  totalSubmissions: number;
  activeThreats: number;
  criticalRisk: number;
  avgRiskScore: number;
  totalApksScanned: number;
  familiesIdentified: number;
  familiesTracked: number;
  newFamilies: number;
  iocsDiscovered: number;
  trend: number[];
}

export async function getKpi(): Promise<KpiResponse> {
  if (isDemo()) return mock.kpiSummary;
  return live<KpiResponse>("/kpi");
}

export interface SubmissionsListResponse {
  items: mock.Submission[];
  total: number;
  page: number;
  pageSize: number;
}

export async function getSubmissions(
  page = 1,
  pageSize = 20
): Promise<SubmissionsListResponse> {
  if (isDemo()) {
    const start = (page - 1) * pageSize;
    return {
      items: mock.submissions.slice(start, start + pageSize),
      total: mock.submissions.length,
      page,
      pageSize,
    };
  }
  return live<SubmissionsListResponse>(
    `/history?page=${page}&page_size=${pageSize}`
  );
}

export async function getSubmission(id: string): Promise<mock.Submission> {
  if (isDemo()) {
    const s = mock.submissions.find((s) => s.id === id);
    if (!s) throw new Error(`Submission ${id} not found in demo data`);
    return s;
  }
  return live<mock.Submission>(`/submissions/${id}`);
}

export interface HuntResponse {
  hits: mock.ThreatHuntHit[];
  total: number;
}

export async function threatHunt(q: string): Promise<HuntResponse> {
  if (isDemo()) {
    const ql = q.toLowerCase();
    const hits = ql
      ? mock.threatHuntHits.filter(
          (h) =>
            h.indicator.toLowerCase().includes(ql) ||
            h.family.toLowerCase().includes(ql) ||
            h.type.includes(ql)
        )
      : mock.threatHuntHits;
    return { hits, total: hits.length };
  }
  return live<HuntResponse>(`/threat-hunt?q=${encodeURIComponent(q)}`);
}

export async function getTAIGGraph(submissionId: string): Promise<mock.TAIGNodes> {
  // We only have one demo graph; serve the same one to all submissions.
  if (isDemo()) return mock.taigGraph;
  return live<mock.TAIGNodes>(`/submissions/${submissionId}/taig`);
}

export async function getRecentEvents(): Promise<typeof mock.recentEvents> {
  return Promise.resolve(mock.recentEvents);
}

export async function getRecentFamilies(): Promise<typeof mock.recentFamilies> {
  return Promise.resolve(mock.recentFamilies);
}
