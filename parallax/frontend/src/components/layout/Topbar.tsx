import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Search } from "lucide-react";

interface TopbarProps {
  title: string;
  eyebrow?: string;
  right?: ReactNode;
  children?: ReactNode;
}

export function Topbar({ title, eyebrow, right, children }: TopbarProps) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  return (
    <header className="sticky top-0 z-30 bg-bone/80 backdrop-blur-sm border-b border-ink/10">
      <div className="px-6 h-16 flex items-center justify-between gap-6">
        <div className="min-w-0">
          {eyebrow && <div className="eyebrow text-ink/50 mb-0.5">{eyebrow}</div>}
          <h1 className="font-display text-2xl leading-none truncate">{title}</h1>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (q.trim()) navigate(`/hunt?q=${encodeURIComponent(q.trim())}`);
          }}
          className="hidden md:flex items-center gap-2 flex-1 max-w-md"
        >
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink/40" strokeWidth={1.6} />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search IOCs, families, hashes — ↵ to hunt"
              className="w-full h-9 pl-9 pr-3 bg-bone-50 border border-ink/10 font-mono text-xs placeholder:text-ink/40 focus:outline-none focus:border-ink"
            />
          </div>
        </form>

        <div className="flex items-center gap-2">
          {right}
          <button
            onClick={() => navigate("/activity")}
            title="Activity stream"
            className="relative inline-flex items-center justify-center w-9 h-9 border border-ink/10 hover:border-ink transition-colors"
          >
            <Bell className="w-4 h-4" strokeWidth={1.6} />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-oxblood" />
          </button>
        </div>
      </div>
      {children && <div className="px-6 pb-4">{children}</div>}
    </header>
  );
}
