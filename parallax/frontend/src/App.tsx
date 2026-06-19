import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Download,
  FileArchive,
  Link as LinkIcon,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Shield,
  UploadCloud,
  XCircle,
  LogOut,
  Lock
} from "lucide-react";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Status = "queued" | "triaging" | "static" | "dynamic" | "reasoning" | "complete" | "failed";

type Submission = {
  id: string;
  file_name: string;
  file_size: number;
  sha256: string;
  md5: string;
  package_name: string | null;
  status: Status;
  priority: string;
  triage_score: number | null;
  final_score: number | null;
  verdict: string | null;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown> | null;
  hypotheses?: Array<{
    id: string;
    claim: string;
    status: string;
    confidence: number;
    irt_label: string;
  }>;
};

type HistoryResponse = {
  items: Submission[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type BatchResponse = {
  batch_id: string;
  total: number;
  submitted: number;
  results: Array<{ file_name?: string; submission_id?: string; status?: string; error?: string }>;
};

type HuntTemplateResponse = { hunts: string[] };
type HuntResponse = { hunt?: string; results?: Array<Record<string, unknown>>; count?: number; error?: string };

const API_BASE_KEY = "parallax.apiBase";
const API_KEY_KEY = "parallax.apiKey";
const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function stored(key: string, fallback: string) {
  return window.sessionStorage.getItem(key) ?? window.localStorage.getItem(key) ?? fallback;
}

function normalizeApiBase(value: string) {
  const trimmed = value.trim() || DEFAULT_API_BASE;
  return trimmed.replace(/\/+$/, "");
}

function apiPath(apiBase: string, path: string) {
  return `${normalizeApiBase(apiBase)}${path.startsWith("/") ? path : `/${path}`}`;
}

function browserUrl(apiBase: string, path: string) {
  return new URL(apiPath(apiBase, path), window.location.origin);
}

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes)) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function statusIcon(status: Status) {
  if (status === "complete") return <CheckCircle2 size={16} />;
  if (status === "failed") return <XCircle size={16} />;
  if (status === "queued") return <Clock3 size={16} />;
  return <Loader2 size={16} className="spin" />;
}

function verdictClass(verdict: string | null) {
  const normalized = (verdict ?? "").toLowerCase();
  if (normalized.includes("high") || normalized.includes("malicious") || normalized.includes("critical")) return "danger";
  if (normalized.includes("clean") || normalized.includes("low")) return "ok";
  if (normalized.includes("medium") || normalized.includes("suspicious")) return "warn";
  return "muted";
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? body.error ?? `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function useApi(apiBase: string, apiKey: string) {
  return useMemo(() => {
    const base = normalizeApiBase(apiBase);
    const headers = () => ({
      ...(apiKey ? { "X-API-Key": apiKey } : {})
    });

    return {
      history: (status: string) => {
        const params = new URLSearchParams({ page: "1", page_size: "30" });
        if (status !== "all") params.set("status", status);
        return fetch(`${base}/history?${params}`, { headers: headers() }).then(
          parseResponse<HistoryResponse>
        );
      },
      status: (id: string) =>
        fetch(`${base}/analysis/${id}`, { headers: headers() }).then(parseResponse<Submission>),
      result: (id: string) =>
        fetch(`${base}/analysis/${id}/result`, { headers: headers() }).then(
          parseResponse<Record<string, unknown>>
        ),
      submit: (files: FileList, webhookUrl: string) => {
        const data = new FormData();
        Array.from(files).forEach((file) => data.append(files.length > 1 ? "files" : "file", file));
        if (webhookUrl.trim()) data.set("webhook_url", webhookUrl.trim());
        const path = files.length > 1 ? "/analyze/batch" : "/analyze";
        return fetch(`${base}${path}`, {
          method: "POST",
          headers: headers(),
          body: data
        }).then(parseResponse<Submission | BatchResponse>);
      },
      quarantineUrl: (id: string) =>
        fetch(`${base}/analysis/${id}/quarantine-url`, { headers: headers() }).then(
          parseResponse<{ url: string; expires_in_seconds: number }>
        ),
      artifactUrl: (id: string, artifact: string) => {
        const url = browserUrl(base, `/analysis/${id}/${artifact}`);
        if (apiKey) url.searchParams.set("api_key", apiKey);
        return url.toString();
      },
      graphHealth: () =>
        fetch(`${base}/graph/health`, { headers: headers() }).then(
          parseResponse<Record<string, unknown>>
        ),
      huntTemplates: () =>
        fetch(`${base}/hunt/templates`, { headers: headers() }).then(
          parseResponse<HuntTemplateResponse>
        ),
      hunt: (hunt: string, query: string) =>
        fetch(`${base}/hunt`, {
          method: "POST",
          headers: { ...headers(), "Content-Type": "application/json" },
          body: JSON.stringify({
            hunt,
            sha256: query,
            family: query,
            technique: query,
            min_score: 60,
            limit: 25
          })
        }).then(parseResponse<HuntResponse>)
    };
  }, [apiBase, apiKey]);
}

export function App() {
  const [apiBase, setApiBase] = useState(() => stored(API_BASE_KEY, DEFAULT_API_BASE));
  const [apiKey, setApiKey] = useState(() => stored(API_KEY_KEY, ""));
  const [isAuthenticated, setIsAuthenticated] = useState(!!apiKey);
  
  const [statusFilter, setStatusFilter] = useState("all");
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [selected, setSelected] = useState<Submission | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [graphHealth, setGraphHealth] = useState<Record<string, unknown> | null>(null);
  const [huntTemplates, setHuntTemplates] = useState<string[]>([]);
  const [huntName, setHuntName] = useState("high_risk_apks");
  const [huntQuery, setHuntQuery] = useState("");
  const [huntResult, setHuntResult] = useState<HuntResponse | null>(null);
  const api = useApi(apiBase, apiKey);

  useEffect(() => {
    window.localStorage.setItem(API_BASE_KEY, apiBase);
    if (isAuthenticated) {
      window.sessionStorage.setItem(API_KEY_KEY, apiKey);
    } else {
      window.sessionStorage.removeItem(API_KEY_KEY);
    }
  }, [apiBase, apiKey, isAuthenticated]);

  // Real-time SSE for History
  useEffect(() => {
    if (!isAuthenticated || !apiKey) return;
    api.history(statusFilter)
      .then((data) => {
        setHistory(data);
        if (!selectedId && data.items.length > 0) {
          setSelectedId(data.items[0].id);
        }
      })
      .catch(() => undefined);

    const url = browserUrl(apiBase, "/history/stream");
    url.searchParams.set("api_key", apiKey);
    if (statusFilter !== "all") url.searchParams.set("status", statusFilter);

    const es = new EventSource(url.toString());
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setHistory(data);
        if (!selectedId && data.items && data.items.length > 0) {
          setSelectedId(data.items[0].id);
        }
      } catch(err) {}
    };
    es.onerror = () => {
      // Silently reconnect
    };
    return () => es.close();
  }, [api, apiBase, apiKey, statusFilter, isAuthenticated, selectedId]);

  // Real-time SSE for Selected Analysis
  useEffect(() => {
    if (!isAuthenticated || !apiKey || !selectedId) return;
    const url = browserUrl(apiBase, `/analysis/${selectedId}/stream`);
    url.searchParams.set("api_key", apiKey);

    const es = new EventSource(url.toString());
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setSelected(data);
      } catch(err) {}
    };
    return () => es.close();
  }, [apiBase, apiKey, selectedId, isAuthenticated]);

  // One-time fetch for static result JSON when selection changes
  useEffect(() => {
    if (!isAuthenticated || !selectedId) {
      setResult(null);
      return;
    }
    api.result(selectedId).then(setResult).catch(() => setResult(null));
  }, [api, selectedId, selected?.status, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    api.graphHealth().then(setGraphHealth).catch(() => setGraphHealth(null));
    api.huntTemplates()
      .then((data) => {
        setHuntTemplates(data.hunts);
        if (data.hunts[0]) setHuntName(data.hunts[0]);
      })
      .catch(() => setHuntTemplates([]));
  }, [api, isAuthenticated]);

  const handleLogin = (e: FormEvent) => {
    e.preventDefault();
    if (apiKey.trim()) {
      setIsAuthenticated(true);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setApiKey("");
    setHistory(null);
    setSelected(null);
  };

  async function submitFiles(event: FormEvent) {
    event.preventDefault();
    if (!files?.length) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await api.submit(files, webhookUrl);
      if ("batch_id" in response) {
        setNotice(`Batch ${response.batch_id}: ${response.submitted}/${response.total} queued`);
      } else {
        setNotice(`${response.file_name} queued`);
        setSelectedId(response.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function issueQuarantineUrl() {
    if (!selected) return;
    try {
      const payload = await api.quarantineUrl(selected.id);
      window.open(payload.url, "_blank", "noopener,noreferrer");
      setNotice(`Signed URL expires in ${payload.expires_in_seconds}s`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create signed URL");
    }
  }

  async function runHunt(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setHuntResult(await api.hunt(huntName, huntQuery));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hunt failed");
    } finally {
      setBusy(false);
    }
  }

  const counts = useMemo(() => {
    const items = history?.items ?? [];
    return {
      total: history?.total ?? 0,
      active: items.filter((item) => !["complete", "failed"].includes(item.status)).length,
      high: items.filter((item) => verdictClass(item.verdict) === "danger").length,
      failed: items.filter((item) => item.status === "failed").length
    };
  }, [history]);

  if (!isAuthenticated) {
    return (
      <main className="landing-page glass-bg">
        <header className="landing-header">
          <div className="brand">
            <Shield size={32} className="glow-icon" />
            <h1>PARALLAX</h1>
          </div>
          <a href="#login" className="glass-btn primary glow-btn">Platform Access</a>
        </header>

        <section className="hero">
          <h1 className="hero-title">Agentic Malware Analysis</h1>
          <p className="hero-subtitle">
            Parallax combines deterministic static analysis with resilient, LLM-driven dynamic execution to identify the true intent of polymorphic Android malware.
          </p>
          <div className="hero-features">
            <div className="feature-card glass-panel">
              <Activity size={32} className="glow-icon" />
              <h3>Two-Layer Risk Scoring</h3>
              <p>Fast deterministic triage combined with deep LLM-driven behavioral confidence scoring.</p>
            </div>
            <div className="feature-card glass-panel">
              <Shield size={32} className="glow-icon" />
              <h3>Graceful Degradation</h3>
              <p>Resilient infrastructure that falls back to static heuristics and local models when under load.</p>
            </div>
            <div className="feature-card glass-panel">
              <Search size={32} className="glow-icon" />
              <h3>Agentic Workflow</h3>
              <p>Autonomous LLM agents that formulate hypotheses and generate dynamic Frida hooks on the fly.</p>
            </div>
          </div>
        </section>

        <section id="login" className="login-section">
          <div className="login-box glass-panel">
            <div className="brand center">
              <Lock size={48} className="glow-icon" />
              <h2>Analyst Portal</h2>
              <span>Secure Platform Access</span>
            </div>
            <form className="login-form" onSubmit={handleLogin}>
              <div className="input-group">
                <Lock size={18} />
                <input
                  type="password"
                  placeholder="Enter Analyst API Key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  required
                />
              </div>
              <button className="primary full-width glow-btn" type="submit">Authenticate</button>
            </form>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="topbar glass-panel">
        <div className="brand">
          <Shield size={28} className="glow-icon" />
          <div>
            <h1>PARALLAX</h1>
            <span>Malware analysis console</span>
          </div>
        </div>
        <div className="connection">
          <input
            aria-label="API base"
            value={apiBase}
            onChange={(event) => setApiBase(event.target.value)}
            className="glass-input"
          />
          <button title="Logout" onClick={handleLogout} className="glass-btn danger-hover">
            <LogOut size={18} /> Logout
          </button>
        </div>
      </header>

      {(error || notice) && (
        <div className={`banner ${error ? "error" : "notice"} glass-panel pop-in`}>
          {error ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
          <span>{error || notice}</span>
        </div>
      )}

      <section className="metrics">
        <Metric label="Total" value={counts.total} icon={<FileArchive size={18} />} />
        <Metric label="Active" value={counts.active} icon={<Activity size={18} className="pulse-icon" />} />
        <Metric label="High Risk" value={counts.high} icon={<AlertTriangle size={18} />} isDanger={counts.high > 0} />
        <Metric label="Failed" value={counts.failed} icon={<XCircle size={18} />} />
      </section>

      <section className="workspace">
        <aside className="left-pane">
          <form className="upload-panel glass-panel" onSubmit={submitFiles}>
            <label className="dropzone">
              <UploadCloud size={28} className="glow-icon" />
              <input
                type="file"
                accept=".apk"
                multiple
                onChange={(event: ChangeEvent<HTMLInputElement>) => setFiles(event.target.files)}
              />
              <span>{files?.length ? `${files.length} APK selected` : "Drag or select APK files"}</span>
            </label>
            <input
              className="wide-input glass-input"
              placeholder="Webhook URL (Optional)"
              value={webhookUrl}
              onChange={(event) => setWebhookUrl(event.target.value)}
            />
            <button className="primary glow-btn" disabled={busy || !files?.length}>
              {busy ? <Loader2 size={18} className="spin" /> : <Play size={18} />}
              <span>Submit Analysis</span>
            </button>
          </form>

          <div className="filter-row">
            {["all", "queued", "triaging", "static", "dynamic", "reasoning", "complete", "failed"].map(
              (status) => (
                <button
                  key={status}
                  className={`glass-btn ${statusFilter === status ? "active glow-border" : ""}`}
                  onClick={() => setStatusFilter(status)}
                >
                  {status}
                </button>
              )
            )}
          </div>

          <div className="submission-list glass-panel no-padding">
            {(history?.items ?? []).map((item) => (
              <button
                key={item.id}
                className={`submission-row ${selectedId === item.id ? "selected" : ""}`}
                onClick={() => setSelectedId(item.id)}
              >
                <span className={`status ${item.status}`}>{statusIcon(item.status)}</span>
                <span className="row-main">
                  <strong>{item.file_name}</strong>
                  <small>{item.sha256.slice(0, 16)} · {formatBytes(item.file_size)}</small>
                </span>
                <span className={`verdict ${verdictClass(item.verdict)}`}>{item.verdict ?? "-"}</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="detail-pane glass-panel">
          {selected ? (
            <div className="fade-in">
              <div className="detail-header">
                <div>
                  <h2>{selected.file_name}</h2>
                  <span className="subtitle">{selected.package_name ?? selected.sha256}</span>
                </div>
                <span className={`verdict large ${verdictClass(selected.verdict)} glow-border`}>
                  {selected.verdict ?? selected.status}
                </span>
              </div>

              <div className="score-grid">
                <Detail label="Status" value={selected.status} />
                <Detail label="Triage" value={selected.triage_score ?? "-"} />
                <Detail label="Final" value={selected.final_score ?? "-"} />
                <Detail label="Updated" value={new Date(selected.updated_at).toLocaleString()} />
              </div>

              <div className="actions">
                <button onClick={issueQuarantineUrl} className="glass-btn" title="Open signed quarantine URL">
                  <LinkIcon size={17} />
                  <span>Raw APK</span>
                </button>
                {["report.html", "report.pdf", "stix", "yara", "fraud-rules"].map((artifact) => (
                  <a
                    key={artifact}
                    href={api.artifactUrl(selected.id, artifact)}
                    className="glass-btn"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download size={17} />
                    <span>{artifact}</span>
                  </a>
                ))}
              </div>

              <div className="split">
                <JsonPanel title="Cortex" data={result?.cortex_result ?? selected.metadata ?? {}} />
                <JsonPanel title="Fraud Chain" data={result?.fraud_chain ?? []} />
              </div>

              <div className="hypotheses">
                {(selected.hypotheses ?? []).map((hypothesis) => (
                  <div key={hypothesis.id} className="hypothesis glass-panel compact">
                    <strong>{hypothesis.claim}</strong>
                    <span className="badge">{hypothesis.irt_label} · {Math.round(hypothesis.confidence * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state fade-in">
              <FileArchive size={48} className="glow-icon" />
              <span>Select an analysis to view details</span>
            </div>
          )}
        </section>

        <aside className="right-pane">
          <section className="panel glass-panel">
            <div className="panel-title">
              <Activity size={18} className="glow-icon" />
              <h3>TAIG Graph</h3>
            </div>
            <JsonPanel title="" data={graphHealth ?? { status: "unavailable" }} compact />
          </section>

          <section className="panel glass-panel">
            <div className="panel-title">
              <Search size={18} className="glow-icon" />
              <h3>Threat Hunt</h3>
            </div>
            <form className="hunt-form" onSubmit={runHunt}>
              <select className="glass-input" value={huntName} onChange={(event) => setHuntName(event.target.value)}>
                {(huntTemplates.length ? huntTemplates : ["high_risk_apks"]).map((hunt) => (
                  <option key={hunt} value={hunt}>
                    {hunt}
                  </option>
                ))}
              </select>
              <input
                className="glass-input"
                placeholder="sha256, family, technique"
                value={huntQuery}
                onChange={(event) => setHuntQuery(event.target.value)}
              />
              <button className="primary glow-btn">
                {busy ? <Loader2 size={18} className="spin" /> : <Search size={18} />}
                <span>Run</span>
              </button>
            </form>
            <JsonPanel title="" data={huntResult ?? { count: 0, results: [] }} compact />
          </section>
        </aside>
      </section>
    </main>
  );
}

function Metric({ label, value, icon, isDanger }: { label: string; value: number; icon: React.ReactNode, isDanger?: boolean }) {
  return (
    <div className={`metric glass-panel ${isDanger ? "danger-glow" : ""}`}>
      <div className="metric-icon">{icon}</div>
      <div className="metric-content">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="detail glass-panel compact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function JsonPanel({
  title,
  data,
  compact = false
}: {
  title: string;
  data: unknown;
  compact?: boolean;
}) {
  return (
    <section className={`json-panel ${compact ? "compact" : ""}`}>
      {title && <h3>{title}</h3>}
      <pre className="glass-code">{JSON.stringify(data, null, 2)}</pre>
    </section>
  );
}
