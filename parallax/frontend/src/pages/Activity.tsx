import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, ShieldCheck, Terminal as TerminalIcon, Activity as ActivityIcon } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Pill } from "../components/primitives/Pill";
import { getRecentEvents } from "../lib/api";
import type { RecentEvent } from "../lib/mock-data";
import { cn } from "../lib/utils";

const kindIcon = {
  danger: AlertTriangle,
  warn: ShieldCheck,
  ok: CheckCircle2,
  info: TerminalIcon,
};

export default function Activity() {
  const [events, setEvents] = useState<RecentEvent[]>([]);

  useEffect(() => {
    void (async () => setEvents(await getRecentEvents()))();
  }, []);

  return (
    <div>
      <Topbar
        eyebrow="System activity"
        title="Stream"
        right={
          <Pill tone="acid">
            <span className="live-dot mr-1" />
            Recording
          </Pill>
        }
      />
      <div className="p-6 max-w-[1600px]">
        <Panel>
          <PanelHeader eyebrow="Live event stream" title="All systems" />
          <ul className="px-6 pb-6 divide-y divide-ink/10 max-h-[70vh] overflow-auto">
            {events.map((e, i) => {
              const Icon = kindIcon[e.kind as keyof typeof kindIcon];
              return (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.02 }}
                  className="py-2.5 flex items-start gap-3 font-mono text-xs"
                >
                  <span className="text-ink/40 w-16 shrink-0">{e.time}</span>
                  <Icon className={cn("w-3.5 h-3.5 mt-0.5 shrink-0", kindColor[e.kind as keyof typeof kindColor])} strokeWidth={1.6} />
                  <span className="flex-1 text-ink/80">{e.text}</span>
                </motion.li>
              );
            })}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

const kindColor: Record<string, string> = {
  danger: "text-oxblood",
  warn: "text-warn",
  ok: "text-ok",
  info: "text-ink/50",
};