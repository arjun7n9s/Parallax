import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Compass,
  Eye,
  KeyRound,
  LogOut,
  Search,
  Settings,
  Sparkles,
  Terminal,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useAuth } from "../../hooks/useAuth";

const nav = [
  { to: "/console", label: "Console", Icon: Terminal },
  { to: "/intel", label: "Threat Intel", Icon: Eye },
  { to: "/hunt", label: "Threat Hunt", Icon: Search },
  { to: "/graph", label: "TAIG Graph", Icon: Compass },
  { to: "/cost", label: "Economics", Icon: BarChart3 },
  { to: "/activity", label: "Activity", Icon: Activity },
] as const;

const secondary = [
  { to: "/settings", label: "Settings", Icon: Settings },
] as const;

export function Sidebar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { signOut, key } = useAuth();

  return (
    <aside className="hidden lg:flex flex-col w-60 shrink-0 border-r border-ink/10 bg-bone-50">
      {/* Brand */}
      <Link to="/" className="flex items-center justify-between px-5 h-16 border-b border-ink/10 group">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-ink flex items-center justify-center">
            <span className="font-display text-bone text-lg leading-none -mt-0.5">P</span>
          </div>
          <div className="font-display text-xl leading-none">PARALLAX</div>
        </div>
        <Sparkles className="w-3.5 h-3.5 text-oxblood opacity-0 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
      </Link>

      <div className="px-5 py-3 flex items-center gap-2">
        <span className="live-dot" />
        <span className="eyebrow">System Online</span>
      </div>

      {/* Primary nav */}
      <nav className="px-3 flex-1">
        <div className="eyebrow px-2 pt-2 pb-1.5">Workflow</div>
        <ul className="space-y-0.5">
          {nav.map(({ to, label, Icon }) => {
            const active = pathname === to || pathname.startsWith(to + "/");
            return (
              <li key={to}>
                <Link
                  to={to}
                  className={cn(
                    "flex items-center gap-2.5 h-9 px-2 text-sm transition-colors",
                    active ? "bg-ink text-bone" : "text-ink/70 hover:text-ink hover:bg-ink/5"
                  )}
                >
                  <Icon className="w-4 h-4" strokeWidth={active ? 2.2 : 1.6} />
                  <span>{label}</span>
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="eyebrow px-2 pt-5 pb-1.5">Account</div>
        <ul className="space-y-0.5">
          {secondary.map(({ to, label, Icon }) => (
            <li key={to}>
              <Link
                to={to}
                className="flex items-center gap-2.5 h-9 px-2 text-sm text-ink/70 hover:text-ink hover:bg-ink/5 transition-colors"
              >
                <Icon className="w-4 h-4" strokeWidth={1.6} />
                <span>{label}</span>
              </Link>
            </li>
          ))}
          <li>
            <button
              onClick={() => {
                signOut();
                navigate("/auth");
              }}
              className="w-full flex items-center gap-2.5 h-9 px-2 text-sm text-ink/70 hover:text-oxblood hover:bg-oxblood/5 transition-colors"
            >
              <LogOut className="w-4 h-4" strokeWidth={1.6} />
              <span>Sign out</span>
            </button>
          </li>
        </ul>
      </nav>

      {/* Key indicator */}
      <div className="m-3 p-3 border border-ink/10 bg-bone-100">
        <div className="flex items-center gap-2 mb-1.5">
          <KeyRound className="w-3 h-3 text-ink/50" strokeWidth={1.6} />
          <div className="eyebrow">Session Key</div>
        </div>
        <div className="font-mono text-[10px] text-ink/70 break-all">
          {key ? `${key.slice(0, 4)}…${key.slice(-4)}` : "—"}
        </div>
      </div>
    </aside>
  );
}
