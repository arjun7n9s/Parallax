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
  XCircle
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
const DEFAULT_API_BASE = "http://localhost:8000/api/v1";
const POLL_MS = 5000;

function stored(key: string, fallback: string) {
  return window.localStorage.getItem(key) ?? fallback;
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
  if (normalized.includes("high") || normalized.includes("malicious")) return "danger";
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
    const headers = () => ({
      ...(apiKey ? { "X-API-Key": apiKey } : {})
    });

    return {
      history: (status: string) => {
        const params = new URLSearchParams({ page: "1", page_size: "30" });
        if (status !== "all") params.set("status", status);
        return fetch(`${apiBase}/history?${params}`, { headers: headers() }).then(
          parseResponse<HistoryResponse>
        );
      },
      status: (id: string) =>
        fetch(`${apiBase}/analysis/${id}`, { headers: headers() }).then(parseResponse<Submission>),
      result: (id: string) =>
        fetch(`${apiBase}/analysis/${id}/result`, { headers: headers() }).then(
          parseResponse<Record<string, unknown>>
        ),
      submit: (files: FileList, webhookUrl: string) => {
        const data = new FormData();
        Array.from(files).forEach((file) => data.append(files.length > 1 ? "files" : "file", file));
        if (webhookUrl.trim()) data.set("webhook_url", webhookUrl.trim());
        const path = files.length > 1 ? "/analyze/batch" : "/analyze";
        return fetch(`${apiBase}${path}`, {
          method: "POST",
          headers: headers(),
          body: data
        }).then(parseResponse<Submission | BatchResponse>);
      },
      quarantineUrl: (id: string) =>
        fetch(`${apiBase}/analysis/${id}/quarantine-url`, { headers: headers() }).then(
          parseResponse<{ url: string; expires_in_seconds: number }>
        ),
      artifactUrl: (id: string, artifact: string) => `${apiBase}/analysis/${id}/${artifact}`,
      graphHealth: () =>
        fetch(`${apiBase}/graph/health`, { headers: headers() }).then(
          parseResponse<Record<string, unknown>>
        ),
      huntTemplates: () =>
        fetch(`${apiBase}/hunt/templates`, { headers: headers() }).then(
          parseResponse<HuntTemplateResponse>
        ),
      hunt: (hunt: string, query: string) =>
        fetch(`${apiBase}/hunt`, {
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

  useEffect(() => window.localStorage.setItem(API_BASE_KEY, apiBase), [apiBase]);
  useEffect(() => window.localStorage.setItem(API_KEY_KEY, apiKey), [apiKey]);

  const refreshHistory = useCallback(async () => {
    try {
      const next = await api.history(statusFilter);
      setHistory(next);
      if (!selectedId && next.items[0]) setSelectedId(next.items[0].id);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    }
  }, [api, selectedId, statusFilter]);

  const refreshSelected = useCallback(async () => {
    if (!selectedId) {
      setSelected(null);
      setResult(null);
      return;
    }
    try {
      const [statusData, resultData] = await Promise.all([
        api.status(selectedId),
        api.result(selectedId).catch(() => null)
      ]);
      setSelected(statusData);
      setResult(resultData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analysis");
    }
  }, [api, selectedId]);

  useEffect(() => {
    refreshHistory();
    const timer = window.setInterval(refreshHistory, POLL_MS);
    return () => window.clearInterval(timer);
  }, [refreshHistory]);

  useEffect(() => {
    refreshSelected();
    const timer = window.setInterval(refreshSelected, POLL_MS);
    return () => window.clearInterval(timer);
  }, [refreshSelected]);

  useEffect(() => {
    api.graphHealth().then(setGraphHealth).catch(() => setGraphHealth(null));
    api.huntTemplates()
      .then((data) => {
        setHuntTemplates(data.hunts);
        if (data.hunts[0]) setHuntName(data.hunts[0]);
      })
      .catch(() => setHuntTemplates([]));
  }, [api]);

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
      await refreshHistory();
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

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <Shield size={28} />
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
          />
          <input
            aria-label="API key"
            type="password"
            placeholder="X-API-Key"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
          />
          <button title="Refresh data" onClick={refreshHistory}>
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      {(error || notice) && (
        <div className={`banner ${error ? "error" : "notice"}`}>
          {error ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
          <span>{error || notice}</span>
        </div>
      )}

      <section className="metrics">
        <Metric label="Total" value={counts.total} icon={<FileArchive size={18} />} />
        <Metric label="Active" value={counts.active} icon={<Activity size={18} />} />
        <Metric label="High Risk" value={counts.high} icon={<AlertTriangle size={18} />} />
        <Metric label="Failed" value={counts.failed} icon={<XCircle size={18} />} />
      </section>

      <section className="workspace">
        <aside className="left-pane">
          <form className="upload-panel" onSubmit={submitFiles}>
            <label className="dropzone">
              <UploadCloud size={24} />
              <input
                type="file"
                accept=".apk"
                multiple
                onChange={(event: ChangeEvent<HTMLInputElement>) => setFiles(event.target.files)}
              />
              <span>{files?.length ? `${files.length} APK selected` : "Select APK files"}</span>
            </label>
            <input
              className="wide-input"
              placeholder="Webhook URL"
              value={webhookUrl}
              onChange={(event) => setWebhookUrl(event.target.value)}
            />
            <button className="primary" disabled={busy || !files?.length}>
              {busy ? <Loader2 size={18} className="spin" /> : <Play size={18} />}
              <span>Submit</span>
            </button>
          </form>

          <div className="filter-row">
            {["all", "queued", "triaging", "static", "dynamic", "reasoning", "complete", "failed"].map(
              (status) => (
                <button
                  key={status}
                  className={statusFilter === status ? "active" : ""}
                  onClick={() => setStatusFilter(status)}
                >
                  {status}
                </button>
              )
            )}
          </div>

          <div className="submission-list">
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

        <section className="detail-pane">
          {selected ? (
            <>
              <div className="detail-header">
                <div>
                  <h2>{selected.file_name}</h2>
                  <span>{selected.package_name ?? selected.sha256}</span>
                </div>
                <span className={`verdict large ${verdictClass(selected.verdict)}`}>
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
                <button onClick={issueQuarantineUrl} title="Open signed quarantine URL">
                  <LinkIcon size={17} />
                  <span>Raw APK</span>
                </button>
                {["report.html", "report.pdf", "stix", "yara", "fraud-rules"].map((artifact) => (
                  <a
                    key={artifact}
                    href={api.artifactUrl(selected.id, artifact)}
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
                  <div key={hypothesis.id} className="hypothesis">
                    <strong>{hypothesis.claim}</strong>
                    <span>{hypothesis.irt_label} · {Math.round(hypothesis.confidence * 100)}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <FileArchive size={36} />
              <span>No submission selected</span>
            </div>
          )}
        </section>

        <aside className="right-pane">
          <section className="panel">
            <div className="panel-title">
              <Activity size={18} />
              <h3>Graph</h3>
            </div>
            <JsonPanel title="" data={graphHealth ?? { status: "unavailable" }} compact />
          </section>

          <section className="panel">
            <div className="panel-title">
              <Search size={18} />
              <h3>Hunt</h3>
            </div>
            <form className="hunt-form" onSubmit={runHunt}>
              <select value={huntName} onChange={(event) => setHuntName(event.target.value)}>
                {(huntTemplates.length ? huntTemplates : ["high_risk_apks"]).map((hunt) => (
                  <option key={hunt} value={hunt}>
                    {hunt}
                  </option>
                ))}
              </select>
              <input
                placeholder="sha256, family, technique"
                value={huntQuery}
                onChange={(event) => setHuntQuery(event.target.value)}
              />
              <button className="primary">
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

function Metric({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="detail">
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
    <section className={compact ? "json-panel compact" : "json-panel"}>
      {title && <h3>{title}</h3>}
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </section>
  );
}
