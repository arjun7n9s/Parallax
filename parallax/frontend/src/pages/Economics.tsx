import { motion } from "framer-motion";
import { Info } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Kpi } from "../components/primitives/Kpi";
import { Distribution } from "../components/primitives/Graph";
import { isDemo } from "../lib/api";

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.04, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] },
  }),
};

export default function Economics() {
  return (
    <div>
      <Topbar eyebrow="Cost guard" title="Economics" />
      <div className="p-6 max-w-[1600px] space-y-6">
        {isDemo() && (
          <div className="flex items-start gap-2 border border-ink/15 bg-bone-50 p-3 font-mono text-[11px] text-ink/70">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" strokeWidth={1.8} />
            <span>
              Illustrative cost figures. Live spend, per-stage cost and budget tracking come from the
              backend's Prometheus metrics on an authenticated deployment.
            </span>
          </div>
        )}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-ink/20 border border-ink/10">
          <motion.div custom={0} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="Today" value="$24.18" delta={-12} trend={[28, 32, 30, 28, 26, 25, 24]} />
          </motion.div>
          <motion.div custom={1} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="This week" value="$148.92" delta={4} trend={[140, 142, 145, 147, 148, 149, 148]} />
          </motion.div>
          <motion.div custom={2} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="Avg / APK" value="$0.16" delta={-8} trend={[0.21, 0.20, 0.19, 0.18, 0.17, 0.17, 0.16]} />
          </motion.div>
          <motion.div custom={3} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="Cache hit rate" value="63" unit="%" delta={5} trend={[55, 57, 59, 60, 61, 62, 63]} emphasis="acid" />
          </motion.div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <motion.div custom={0} initial="hidden" animate="show" variants={fadeUp} className="col-span-12 lg:col-span-8">
            <Panel>
              <PanelHeader
                eyebrow="Last 14 days"
                title="Daily spend"
                right={<span className="font-mono text-[10px] uppercase tracking-widest text-ink/50">USD</span>}
              />
              <div className="p-6">
                <CostChart />
              </div>
            </Panel>
          </motion.div>
          <motion.div custom={1} initial="hidden" animate="show" variants={fadeUp} className="col-span-12 lg:col-span-4">
            <Panel>
              <PanelHeader eyebrow="By stage" title="Cost breakdown" />
              <div className="px-6 pb-5">
                <Distribution
                  items={[
                    { label: "Reasoning", value: 88, color: "#7C1F2D" },
                    { label: "Static", value: 12, color: "#0A0A0A" },
                    { label: "Dynamic", value: 41, color: "#0A0A0A" },
                    { label: "Delivery", value: 9, color: "#0A0A0A66" },
                  ]}
                />
              </div>
            </Panel>
          </motion.div>
        </div>

        <motion.div custom={2} initial="hidden" animate="show" variants={fadeUp}>
          <Panel variant="ink">
            <PanelHeader
              eyebrow={<span className="text-bone/60">Budget</span>}
              title={<span className="text-bone">$24.18 of $50 spent · 48%</span>}
            />
            <div className="px-6 pb-6">
              <div className="h-2 bg-bone/10 relative">
                <div className="absolute inset-y-0 left-0 bg-acid" style={{ width: "48%" }} />
                <div className="absolute inset-y-0 left-0 border-r border-bone" style={{ left: "80%" }} />
              </div>
              <div className="flex justify-between mt-2 font-mono text-[10px] text-bone/60">
                <span>0</span>
                <span>· $25 cap reached at 14:32 today</span>
                <span>$50</span>
              </div>
            </div>
          </Panel>
        </motion.div>
      </div>
    </div>
  );
}

function CostChart() {
  // 14 days, deterministic data
  const data = [22, 25, 28, 24, 26, 30, 28, 24, 22, 26, 28, 30, 27, 24];
  const max = 40;
  const W = 760, H = 200, pad = 24;
  const step = (W - pad * 2) / (data.length - 1);
  const path = data
    .map((v, i) => {
      const x = pad + i * step;
      const y = H - pad - ((v / max) * (H - pad * 2));
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const area = `${path} L${pad + (data.length - 1) * step},${H - pad} L${pad},${H - pad} Z`;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-48">
        <defs>
          <linearGradient id="cost-area" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#7C1F2D" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#7C1F2D" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((p) => (
          <line
            key={p}
            x1={pad}
            x2={W - pad}
            y1={pad + (H - pad * 2) * p}
            y2={pad + (H - pad * 2) * p}
            stroke="#0A0A0A"
            strokeOpacity="0.08"
          />
        ))}
        <path d={area} fill="url(#cost-area)" />
        <path d={path} fill="none" stroke="#7C1F2D" strokeWidth="1.5" />
        {data.map((v, i) => {
          const x = pad + i * step;
          const y = H - pad - ((v / max) * (H - pad * 2));
          return <circle key={i} cx={x} cy={y} r="2" fill="#7C1F2D" />;
        })}
      </svg>
      <div className="flex justify-between mt-3 font-mono text-[10px] uppercase tracking-widest text-ink/50">
        {["Jun 7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"].map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
    </div>
  );
}