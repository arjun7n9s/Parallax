import { useMemo, useState } from "react";
import { cn } from "../../lib/utils";
import { Maximize2, Minimize2 } from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  type: "class" | "method" | "string" | "permission" | "ioc";
  x?: number;
  y?: number;
}

interface GraphEdge {
  from: string;
  to: string;
  relationship: string;
}

interface TAIGGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  className?: string;
}

/** Tiered layout: permissions → classes → methods → strings/iocs.
 *  No force simulation needed for the demo — positions are deterministic. */
export function TAIGGraph({ nodes, edges, height = 480, className }: TAIGGraphProps) {
  const [fullscreen, setFullscreen] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  const positioned = useMemo(() => layoutNodes(nodes), [nodes]);

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden border border-ink bg-bone-100",
        fullscreen ? "fixed inset-4 z-50 h-auto" : "",
        className
      )}
      style={fullscreen ? {} : { height }}
    >
      <button
        onClick={() => setFullscreen(!fullscreen)}
        className="absolute top-3 right-3 z-10 inline-flex items-center gap-1.5 px-2 h-7 text-[10px] font-mono uppercase tracking-widest bg-bone-50 border border-ink/20 hover:border-ink transition-colors"
      >
        {fullscreen ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
        {fullscreen ? "Close" : "Expand"}
      </button>

      <svg viewBox="0 0 1000 480" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#0A0A0A" />
          </marker>
        </defs>

        {/* Edges */}
        <g stroke="#0A0A0A" strokeWidth="0.5" opacity="0.5">
          {edges.map((e, i) => {
            const from = positioned.find((n) => n.id === e.from);
            const to = positioned.find((n) => n.id === e.to);
            if (!from || !to) return null;
            const isHighlighted = hovered === e.from || hovered === e.to;
            return (
              <line
                key={i}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={isHighlighted ? "#7C1F2D" : "#0A0A0A"}
                strokeWidth={isHighlighted ? 1.5 : 0.5}
                opacity={hovered && !isHighlighted ? 0.15 : 1}
                markerEnd="url(#arrow)"
              />
            );
          })}
        </g>

        {/* Nodes */}
        {positioned.map((n) => {
          const isHovered = hovered === n.id;
          const connected = hovered
            ? edges.some(
                (ed) =>
                  (ed.from === hovered && ed.to === n.id) ||
                  (ed.to === hovered && ed.from === n.id)
              )
            : true;
          const opacity = hovered && !isHovered && !connected ? 0.2 : 1;
          return (
            <g
              key={n.id}
              transform={`translate(${n.x}, ${n.y})`}
              opacity={opacity}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              className="cursor-pointer"
            >
              {nodeShape(n, isHovered)}
              <text
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={n.type === "class" ? 11 : 9}
                fontWeight={n.type === "class" ? 600 : 500}
                fontFamily="Geist Mono, monospace"
                fill={n.type === "permission" || n.type === "ioc" ? "#F4F1EA" : "#0A0A0A"}
              >
                {truncateLabel(n.label, 18)}
              </text>
              {n.type !== "class" && (
                <text
                  textAnchor="middle"
                  dominantBaseline="middle"
                  dy={14}
                  fontSize={7}
                  fontFamily="Geist Mono, monospace"
                  fill="#0A0A0A"
                  opacity="0.5"
                >
                  {n.type}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex items-center gap-3 px-2.5 h-7 bg-bone-50/90 border border-ink/20 text-[10px] font-mono uppercase tracking-widest">
        {(["permission", "class", "method", "ioc", "string"] as const).map((t) => (
          <div key={t} className="flex items-center gap-1.5">
            <div className={cn("w-2.5 h-2.5", legendColor(t))} />
            <span>{t}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function e_to(e: { from: string; to: string }, h: string, n: string) { return e.to === h && e.from === n; }
function e_from(e: { from: string; to: string }, h: string, n: string) { return e.from === h && e.to === n; }

function legendColor(type: string) {
  switch (type) {
    case "permission": return "bg-ink";
    case "class":      return "bg-bone-50 border border-ink";
    case "method":     return "bg-acid";
    case "ioc":        return "bg-oxblood";
    case "string":     return "bg-ochre";
    default:           return "bg-ink/20";
  }
}

function nodeShape(n: GraphNode, isHovered: boolean) {
  const base = isHovered ? 1.2 : 1;
  switch (n.type) {
    case "permission":
      return <rect x={-50 * base} y={-12 * base} width={100 * base} height={24 * base} fill="#0A0A0A" />;
    case "class":
      return <rect x={-55 * base} y={-15 * base} width={110 * base} height={30 * base} fill="#F4F1EA" stroke="#0A0A0A" strokeWidth={1.5 * base} />;
    case "method":
      return <rect x={-45 * base} y={-11 * base} width={90 * base} height={22 * base} fill="#9FE870" />;
    case "ioc":
      return <rect x={-60 * base} y={-12 * base} width={120 * base} height={24 * base} fill="#7C1F2D" />;
    case "string":
      return <rect x={-50 * base} y={-11 * base} width={100 * base} height={22 * base} fill="#C9923A" />;
  }
}

function truncateLabel(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function layoutNodes(nodes: GraphNode[]): GraphNode[] {
  const tiers: Record<string, number> = {
    permission: 0,
    class: 1,
    method: 2,
    string: 3,
    ioc: 3,
  };
  const grouped: Record<number, GraphNode[]> = {};
  nodes.forEach((n) => {
    const t = tiers[n.type] ?? 1;
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(n);
  });
  const W = 1000, H = 480;
  return nodes.map((n) => {
    const tier = tiers[n.type] ?? 1;
    const group = grouped[tier];
    const idx = group.indexOf(n);
    const x = ((idx + 1) / (group.length + 1)) * W;
    const y = ((tier + 0.5) / 4) * H;
    return { ...n, x, y };
  });
}

/** A small inline version of a horizontal bar chart for distribution. */
export function Distribution({
  items,
  className,
}: {
  items: { label: string; value: number; color?: string }[];
  className?: string;
}) {
  const max = Math.max(...items.map((i) => i.value));
  return (
    <div className={cn("space-y-2", className)}>
      {items.map((it) => {
        const pct = (it.value / max) * 100;
        return (
          <div key={it.label} className="flex items-center gap-3">
            <div className="w-24 font-mono text-xs text-ink/70 shrink-0">{it.label}</div>
            <div className="flex-1 h-6 bg-ink/5 relative overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 transition-all duration-700 ease-editorial"
                style={{ width: `${pct}%`, background: it.color || "#0A0A0A" }}
              />
              <div className="absolute inset-y-0 right-1 flex items-center font-mono text-[10px] text-ink/70">
                {it.value}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
