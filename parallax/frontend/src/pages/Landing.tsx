import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../hooks/useAuth";
import {
  ArrowUpRight,
  Brain,
  Eye,
  GitBranch,
  Layers,
  Microscope,
  Network,
  PlayCircle,
  Search,
  ShieldCheck,
  Terminal,
  Zap,
} from "lucide-react";
import { Ticker } from "../components/layout/Ticker";
import { tickerItems } from "../lib/mock-data";

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] } },
};

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

export default function Landing() {
  const navigate = useNavigate();
  const { signIn, signOut, key } = useAuth();
  // Drop straight into the demo console — no auth-page flash.
  const startDemo = () => {
    signIn("demo-7c1f2d-a87e9-9fe870");
    navigate("/console");
  };
  // Always land on the real sign-in form; clear a leftover demo session first.
  const openConsole = () => {
    if (key?.startsWith("demo-")) signOut();
    navigate("/auth");
  };

  return (
    <div className="min-h-screen bg-bone text-ink">
      {/* ============ Top Bar ============ */}
      <header className="sticky top-0 z-30 bg-bone/90 backdrop-blur-sm border-b border-ink/10">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-ink flex items-center justify-center">
              <span className="font-display text-bone text-lg leading-none -mt-0.5">P</span>
            </div>
            <span className="font-display text-xl">PARALLAX</span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm">
            <a href="#capability" className="hover:text-oxblood transition-colors">Capability</a>
            <a href="#architecture" className="hover:text-oxblood transition-colors">Architecture</a>
            <a href="#evidence" className="hover:text-oxblood transition-colors">Live Evidence</a>
            <a href="#open" className="hover:text-oxblood transition-colors">Open Source</a>
          </nav>
          <div className="flex items-center gap-2">
            <button onClick={startDemo} className="btn-ghost hidden sm:inline-flex">
              Try the demo
            </button>
            <button onClick={openConsole} className="btn-primary">
              Analyst Console
              <ArrowUpRight className="w-4 h-4" strokeWidth={2} />
            </button>
          </div>
        </div>
      </header>

      <Ticker items={tickerItems.slice(0, 4)} />

      {/* ============ Hero ============ */}
      <section className="relative">
        <div className="max-w-[1400px] mx-auto px-6 pt-12 pb-20">
          <motion.div
            initial="hidden"
            animate="show"
            variants={stagger}
            className="grid grid-cols-12 gap-6"
          >
            <motion.div variants={fadeUp} className="col-span-12 lg:col-span-8">
              <div className="eyebrow mb-5 flex items-center gap-2">
                <span className="w-6 h-px bg-ink" />
                Agentic malware analysis · v0.1.0
              </div>
              <h1 className="font-display text-display-2xl text-balance">
                The <em className="italic text-oxblood">uncomfortable</em> truth,<br />
                in twelve seconds.
              </h1>
              <p className="mt-8 max-w-2xl text-lg text-ink/70 leading-relaxed text-pretty">
                PARALLAX is a multi-agent analyst that reverse-engineers Android malware end-to-end —
                static analysis, dynamic Frida hooks, attribution, and a signed evidence bundle — and
                argues with itself in a chat room until the verdict stops moving.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <button onClick={startDemo} className="btn-primary h-12 px-6 text-base">
                  <PlayCircle className="w-4 h-4" strokeWidth={2} />
                  Try the live demo
                </button>
                <button onClick={openConsole} className="btn h-12 px-6 text-base">
                  Open analyst console
                  <ArrowUpRight className="w-4 h-4" strokeWidth={2} />
                </button>
                <a
                  href="https://github.com/arjun7n9s/Parallax"
                  className="font-mono text-xs text-ink/60 hover:text-ink ml-2"
                >
                  github.com/arjun7n9s/Parallax ↗
                </a>
              </div>
            </motion.div>

            <motion.aside variants={fadeUp} className="col-span-12 lg:col-span-4">
              <div className="border border-ink p-6 h-full bg-bone-50 relative">
                <div className="absolute -top-px -right-px bg-ink text-bone px-2 h-6 inline-flex items-center eyebrow">
                  In production
                </div>
                <div className="eyebrow mb-4">A typical case</div>
                <div className="font-display text-3xl leading-none">12s</div>
                <div className="font-mono text-xs text-ink/60 mt-1">mean verdict latency</div>
                <div className="rule my-5" />
                <dl className="space-y-3 font-mono text-xs">
                  <Row k="Static analysis" v="2.4s" />
                  <Row k="Dynamic hooks" v="3.1s · 4 hooks" />
                  <Row k="LLM reasoning" v="6.2s · 2 layers" />
                  <Row k="Evidence bundle" v="0.3s · SHA-256" />
                </dl>
                <div className="rule my-5" />
                <div className="flex items-center gap-2 text-xs">
                  <span className="live-dot" />
                  <span className="font-mono text-ink/70">$0.16 / analysis</span>
                </div>
              </div>
            </motion.aside>
          </motion.div>
        </div>
      </section>

      {/* ============ Architecture pipeline ============ */}
      <section id="architecture" className="border-y border-ink bg-ink text-bone">
        <div className="max-w-[1400px] mx-auto px-6 py-20">
          <div className="eyebrow text-bone/60 mb-5 flex items-center gap-2">
            <span className="w-6 h-px bg-bone" /> The pipeline
          </div>
          <h2 className="font-display text-display-lg text-balance mb-12">
            Five stages, one <em className="italic text-acid">uncomfortable</em> answer.
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-px bg-bone/20">
            {STAGES.map((s, i) => (
              <Stage key={s.id} {...s} index={i + 1} />
            ))}
          </div>
        </div>
      </section>

      {/* ============ Capability ============ */}
      <section id="capability" className="max-w-[1400px] mx-auto px-6 py-20">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-4">
            <div className="eyebrow mb-4">What it does</div>
            <h3 className="font-display text-display-md text-balance">
              Eight agents.<br />One verdict.<br />Zero hand-waving.
            </h3>
            <p className="mt-5 text-ink/70 leading-relaxed">
              Every stage has a specialist. Every specialist can challenge any other.
              The case room is a chat, not a queue — disagreements are surfaced, not averaged out.
            </p>
          </div>

          <div className="col-span-12 lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-px bg-ink/20">
            {CAPABILITIES.map((c) => (
              <Capability key={c.title} {...c} />
            ))}
          </div>
        </div>
      </section>

      {/* ============ Live evidence ============ */}
      <section id="evidence" className="bg-bone-100 border-y border-ink">
        <div className="max-w-[1400px] mx-auto px-6 py-20">
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-12 lg:col-span-5">
              <div className="eyebrow mb-4">Live evidence</div>
              <h3 className="font-display text-display-md text-balance">
                Not a marketing video.<br />A <em className="italic text-oxblood">real</em> chat room.
              </h3>
              <p className="mt-5 text-ink/70 leading-relaxed">
                The eight PARALLAX agents collaborating in a live Band room over a real
                banking-trojan case — reasoning over the actual evidence bundle, challenging each
                other, and converging on an action packet. No script, no actors. This is the system.
              </p>
              <div className="mt-6 flex items-center gap-3">
                <button onClick={startDemo} className="btn-primary">
                  Open the demo
                  <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="col-span-12 lg:col-span-7">
              <div className="relative border border-ink bg-ink">
                <video
                  className="block w-full aspect-video"
                  src="/agents-case-room.mp4"
                  controls
                  playsInline
                  preload="metadata"
                  poster="/favicon.svg"
                >
                  Your browser does not support the video tag.
                </video>
                <div className="flex items-center justify-between px-4 py-2 border-t border-bone/15 text-bone">
                  <div className="eyebrow text-bone/70">Band case room · recorded</div>
                  <div className="font-mono text-[10px] text-bone/60">8 agents · real PARALLAX evidence</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ Stats / manifesto ============ */}
      <section className="max-w-[1400px] mx-auto px-6 py-20">
        <div className="border border-ink p-8 sm:p-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <Stat n="371" l="Tests passing" tone="ink" />
            <Stat n="~$0.16" l="Per APK" tone="ink" />
            <Stat n="5-stage" l="Analysis pipeline" tone="oxblood" />
            <Stat n="8" l="Agents in a room" tone="ink" />
          </div>
        </div>
      </section>

      {/* ============ Open source / repo ============ */}
      <section id="open" className="border-t border-ink bg-bone-50">
        <div className="max-w-[1400px] mx-auto px-6 py-16">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div>
              <div className="eyebrow mb-3">Source of truth</div>
              <h3 className="font-display text-display-md">Apache 2.0 · public repo · 22,000+ lines</h3>
              <p className="mt-3 font-mono text-xs text-ink/60 max-w-xl">
                Every claim above has a commit. Every diagram is a Python script. Every agent's prompt is a
                checked-in file. The whole thing runs on a 4-core box.
              </p>
            </div>
            <a
              href="https://github.com/arjun7n9s/Parallax"
              target="_blank"
              rel="noreferrer"
              className="btn h-12 px-6 text-base self-start md:self-end"
            >
              <GitBranch className="w-4 h-4" />
              Read the code
              <ArrowUpRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-ink/10">
        <div className="max-w-[1400px] mx-auto px-6 py-8 flex flex-col md:flex-row justify-between gap-4 font-mono text-[10px] uppercase tracking-widest text-ink/50">
          <div>© 2026 Kunapareddy Tejesh · Apache 2.0</div>
          <div className="flex items-center gap-4">
            <span>FRIDA 16.7.19</span>
            <span>·</span>
            <span>BUILT IN PUBLIC</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-ink/60">{k}</dt>
      <dd className="text-ink tabular-nums">{v}</dd>
    </div>
  );
}

function Stage({ id, Icon, title, body, index }: {
  id: string;
  Icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  body: string;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10%" }}
      transition={{ duration: 0.5, delay: index * 0.05, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] }}
      className="bg-ink p-6 sm:p-7 h-full flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <Icon className="w-5 h-5 text-acid" strokeWidth={1.6} />
        <div className="eyebrow text-bone/40">{id}</div>
      </div>
      <div className="font-display text-2xl leading-tight">{title}</div>
      <div className="font-mono text-xs text-bone/60 leading-relaxed">{body}</div>
    </motion.div>
  );
}

function Capability({ Icon, title, body }: {
  Icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  body: string;
}) {
  return (
    <div className="bg-bone-50 p-6 flex flex-col gap-3">
      <Icon className="w-5 h-5 text-ink" strokeWidth={1.6} />
      <div className="font-display text-xl leading-tight">{title}</div>
      <div className="text-sm text-ink/70 leading-relaxed">{body}</div>
    </div>
  );
}

function Stat({ n, l, tone = "ink" }: { n: string; l: string; tone?: "ink" | "oxblood" }) {
  return (
    <div>
      <div className={`font-display text-5xl md:text-6xl leading-none ${tone === "oxblood" ? "text-oxblood" : "text-ink"}`}>
        {n}
      </div>
      <div className="eyebrow mt-3">{l}</div>
    </div>
  );
}

const STAGES = [
  { id: "01 · triage",   Icon: Search,     title: "Triage",         body: "Unzip, hash, and rate the APK against a calibrated model. Skip the expensive stages for clean apps." },
  { id: "02 · static",   Icon: Microscope, title: "Static analysis", body: "Androguard + jadx decompile. Map permissions, find suspicious APIs, and rank by family similarity." },
  { id: "03 · dynamic",  Icon: Terminal,   title: "Dynamic hooks",  body: "Frida scripts auto-generated by the Hook Planner. Real SMS, network, and accessibility calls captured live." },
  { id: "04 · reasoning",Icon: Brain,      title: "Multi-agent reasoning", body: "Eight specialists debate in a Band chat room. Static Analyst challenges Dynamic. Evidence Validator challenges everyone." },
  { id: "05 · delivery", Icon: ShieldCheck,title: "Delivery",        body: "Signed evidence bundle, Prometheus metrics, Grafana panel, webhook dispatch, JSON+PDF report." },
];

const CAPABILITIES = [
  { Icon: Network,    title: "TAIG Graph", body: "Threat-Annotated Instruction Graph — every permission, class, method, and IOC laid out as a navigable tiered graph." },
  { Icon: Search,     title: "Threat Hunt", body: "Cross-submission IOC matching. Find every APK that touched a given IP, hash, permission, or C2 endpoint." },
  { Icon: Layers,     title: "Two-layer risk", body: "Layer 1: model + rules. Layer 2: LLM reasoning. They must agree, or the verdict is escalated." },
  { Icon: Eye,        title: "Drift detection", body: "Every verdict feeds back into calibration. The system gets sharper on the families it has seen." },
  { Icon: Zap,        title: "Graceful degrade", body: "If the emulator dies, the static verdict still ships. If the LLM times out, the model verdict still ships. Always an answer." },
  { Icon: GitBranch,  title: "Full lineage", body: "Every claim links to the run, the prompt, the source code, the model version, and the cost. Auditable by default." },
];
