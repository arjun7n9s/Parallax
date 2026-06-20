import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Bell,
  Brain,
  CircuitBoard,
  Clock,
  Cpu,
  Database,
  KeyRound,
  LineChart,
  ShieldCheck,
  Sparkles,
  User2,
  Webhook,
  Zap,
} from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { useAuth } from "../hooks/useAuth";
import { cn } from "../lib/utils";

export default function Settings() {
  const { key } = useAuth();
  return (
    <div>
      <Topbar eyebrow="Account" title="Settings" />
      <div className="p-6 max-w-[1400px] grid grid-cols-12 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="col-span-12 lg:col-span-7 space-y-6"
        >
          <Panel>
            <PanelHeader eyebrow="Profile" title="You" />
            <div className="px-6 pb-6 space-y-4 font-mono text-xs">
              <Row k="Display name" v="analyst@parallax" />
              <Row k="Tenant" v="demo" />
              <Row k="Role" v="SOC Analyst · L2" />
              <Row k="API key" v={key ? `${key.slice(0, 6)}…${key.slice(-4)}` : "—"} />
              <Row k="2FA" v="TOTP configured" />
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Notifications" title="When to ping you" />
            <div className="px-6 pb-5 space-y-3 font-mono text-xs">
              <Toggle label="Critical verdict (≥ 9.0)" defaultOn />
              <Toggle label="High verdict (≥ 7.0)" defaultOn />
              <Toggle label="Sandbox crash" defaultOn />
              <Toggle label="Daily digest at 09:00" />
              <Toggle label="Weekly cost report" defaultOn />
              <Toggle label="Family newly identified" />
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Integrations" title="Webhooks" />
            <div className="px-6 pb-5 space-y-2 font-mono text-xs">
              <Integration name="Slack" url="hooks.slack.com/services/T0…/B0…/8x…" on />
              <Integration name="PagerDuty" url="events.pagerduty.com/v2/enqueue" on />
              <Integration name="Splunk HEC" url="splunk.example.com:8088/services/collector" />
              <Integration name="Custom webhook" url="https://your.api/parallax" />
            </div>
          </Panel>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="col-span-12 lg:col-span-5 space-y-6"
        >
          <Panel variant="ink">
            <PanelHeader
              eyebrow={<span className="text-bone/60">Cost guard</span>}
              title={<span className="text-bone">Set your ceiling</span>}
            />
            <div className="px-6 pb-6 space-y-5">
              <div>
                <div className="flex items-baseline justify-between mb-2">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-bone/60">Daily budget</span>
                  <span className="font-display text-2xl">$50</span>
                </div>
                <div className="h-1.5 bg-bone/10">
                  <div className="h-full bg-acid" style={{ width: "48%" }} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {["$10", "$25", "$50", "$100", "$250", "—"].map((v) => (
                  <button key={v} className="h-9 border border-bone/20 text-bone/80 hover:bg-bone/10 font-mono text-xs">
                    {v}
                  </button>
                ))}
              </div>
              <div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-bone/60 mb-2">Behavior on hit</div>
                <div className="flex gap-2">
                  <button className="h-9 px-3 border border-bone bg-bone text-ink font-mono text-xs">Stop & notify</button>
                  <button className="h-9 px-3 border border-bone/20 text-bone/80 font-mono text-xs">Throttle to LLM-lite</button>
                </div>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Model stack" title="Reasoning" />
            <div className="px-6 pb-5 space-y-3 font-mono text-xs">
              <Row k="Layer 1" v="Static rules + embeddings" />
              <Row k="Layer 2" v="Claude Sonnet 4 · reasoning" />
              <Row k="Layer 3" v="Claude Haiku · static summary" />
              <Row k="Embeddings" v="nomic-embed-v1.5 (local)" />
            </div>
          </Panel>
        </motion.div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-ink/50">{k}</span>
      <span className="text-ink truncate">{v}</span>
    </div>
  );
}

function Toggle({ label, defaultOn }: { label: string; defaultOn?: boolean }) {
  return (
    <label className="flex items-center justify-between cursor-pointer group">
      <span className="text-ink/80 group-hover:text-ink">{label}</span>
      <span
        className={cn(
          "w-9 h-5 border border-ink/20 transition-colors relative",
          defaultOn ? "bg-ink" : "bg-bone-100"
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 w-3.5 h-3.5 transition-transform",
            defaultOn ? "bg-bone translate-x-4" : "bg-ink translate-x-0.5"
          )}
        />
      </span>
    </label>
  );
}

function Integration({ name, url, on }: { name: string; url: string; on?: boolean }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <span className={cn("w-1.5 h-1.5 rounded-full", on ? "bg-acid" : "bg-ink/20")} />
      <span className="font-mono text-xs text-ink w-32 shrink-0">{name}</span>
      <span className="font-mono text-[11px] text-ink/50 truncate flex-1">{url}</span>
      <span className={cn("font-mono text-[10px] uppercase tracking-widest", on ? "text-acid" : "text-ink/40")}>
        {on ? "connected" : "off"}
      </span>
    </div>
  );
}