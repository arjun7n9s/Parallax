import { useEffect, useState } from "react";

/** Rolling ticker that displays system activity across the top of the app. */
export function Ticker({ items }: { items: string[] }) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % items.length), 4000);
    return () => clearInterval(t);
  }, [items.length]);

  return (
    <div className="border-y border-ink bg-ink text-bone overflow-hidden">
      <div className="flex items-stretch">
        <div className="shrink-0 px-3 h-9 flex items-center gap-2 border-r border-bone/20 bg-oxblood text-bone">
          <span className="live-dot" />
          <span className="eyebrow text-bone/80">Live</span>
        </div>
        <div className="flex-1 overflow-hidden relative h-9">
          <div
            className="absolute inset-x-0 top-0 flex flex-col transition-transform duration-500 ease-editorial"
            style={{ transform: `translateY(-${idx * 36}px)` }}
          >
            {items.map((it, i) => (
              <div
                key={i}
                className="h-9 flex items-center px-6 font-mono text-xs text-bone/80 whitespace-nowrap"
              >
                {it}
              </div>
            ))}
          </div>
        </div>
        <div className="shrink-0 px-3 h-9 flex items-center gap-2 border-l border-bone/20 font-mono text-[10px] uppercase tracking-widest text-bone/60">
          {String(idx + 1).padStart(2, "0")} / {String(items.length).padStart(2, "0")}
        </div>
      </div>
    </div>
  );
}
