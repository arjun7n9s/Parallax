import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
import { cn } from "../../lib/utils";

interface JsonViewProps {
  data: unknown;
  defaultOpen?: boolean;
  maxDepth?: number;
  className?: string;
  rootLabel?: string;
}

/** A tree-rendered JSON viewer with type-coloured keys. */
export function JsonView({
  data,
  defaultOpen = true,
  maxDepth = 8,
  className,
  rootLabel = "root",
}: JsonViewProps) {
  return (
    <div className={cn("font-mono text-xs leading-relaxed", className)}>
      <Node value={data} label={rootLabel} depth={0} maxDepth={maxDepth} defaultOpen={defaultOpen} />
    </div>
  );
}

function Node({
  value,
  label,
  depth,
  maxDepth,
  defaultOpen,
}: {
  value: unknown;
  label: string;
  depth: number;
  maxDepth: number;
  defaultOpen: boolean;
}) {
  const isObject = value !== null && typeof value === "object" && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const isCollapsible = (isObject || isArray) && depth < maxDepth;
  const [open, setOpen] = useState(defaultOpen && depth < 2);

  if (value === null) {
    return <Line label={label} value="null" tone="muted" />;
  }
  if (value === undefined) {
    return <Line label={label} value="undefined" tone="muted" />;
  }
  if (typeof value === "boolean") {
    return <Line label={label} value={String(value)} tone="ok" />;
  }
  if (typeof value === "number") {
    return <Line label={label} value={String(value)} tone="warn" />;
  }
  if (typeof value === "string") {
    return <Line label={label} value={JSON.stringify(value)} tone="bone" />;
  }
  if (isArray) {
    return (
      <div>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-start gap-1 hover:text-ink w-full text-left"
        >
          {open ? <ChevronDown className="w-3 h-3 mt-1 shrink-0" /> : <ChevronRight className="w-3 h-3 mt-1 shrink-0" />}
          <span className="text-ink/60">{label}</span>
          <span className="text-ink/40">[{value.length}]</span>
        </button>
        {open && (
          <div className="ml-3 border-l border-ink/10 pl-3">
            {value.length === 0 && <span className="text-ink/40">[]</span>}
            {value.map((v, i) => (
              <Node
                key={i}
                value={v}
                label={String(i)}
                depth={depth + 1}
                maxDepth={maxDepth}
                defaultOpen={defaultOpen}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
  if (isObject) {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-start gap-1 hover:text-ink w-full text-left"
        >
          {open ? <ChevronDown className="w-3 h-3 mt-1 shrink-0" /> : <ChevronRight className="w-3 h-3 mt-1 shrink-0" />}
          <span className="text-ink/60">{label}</span>
          <span className="text-ink/40">&#123;{entries.length}&#125;</span>
        </button>
        {open && isCollapsible && (
          <div className="ml-3 border-l border-ink/10 pl-3">
            {entries.length === 0 && <span className="text-ink/40">&#123;&#125;</span>}
            {entries.map(([k, v]) => (
              <Node
                key={k}
                value={v}
                label={k}
                depth={depth + 1}
                maxDepth={maxDepth}
                defaultOpen={defaultOpen}
              />
            ))}
          </div>
        )}
        {open && !isCollapsible && (
          <div className="ml-3 border-l border-ink/10 pl-3">
            <pre className="text-ink/70 whitespace-pre-wrap break-all">
              {JSON.stringify(value, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }
  return <Line label={label} value={String(value)} tone="muted" />;
}

function Line({ label, value, tone }: { label: string; value: string; tone: "ok" | "warn" | "muted" | "bone" }) {
  const valueClass = {
    ok: "text-ok",
    warn: "text-warn",
    bone: "text-ink",
    muted: "text-ink/40",
  }[tone];
  return (
    <div className="flex items-start gap-1">
      <span className="text-ink/50 shrink-0">{label}:</span>
      <span className={cn("break-all", valueClass)}>{value}</span>
    </div>
  );
}

export function CopyableText({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className={cn(
        "inline-flex items-center gap-2 font-mono text-xs text-ink/70 hover:text-ink",
        className
      )}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-ok" /> : <Copy className="w-3.5 h-3.5" />}
      <span>{text}</span>
    </button>
  );
}
