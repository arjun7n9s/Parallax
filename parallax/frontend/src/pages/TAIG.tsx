import { Loader2 } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Pill } from "../components/primitives/Pill";
import { TAIGGraph } from "../components/primitives/Graph";
import { getSubmissions, getTAIGGraph, isDemo } from "../lib/api";
import { useAsync } from "../hooks/useAsync";

export default function TAIG() {
  // Anchor the graph on the most recent real submission (demo serves a seeded graph).
  const graph = useAsync(async () => {
    if (isDemo()) return getTAIGGraph("demo");
    const { items } = await getSubmissions(1, 1);
    return getTAIGGraph(items[0]?.id ?? "demo");
  }, []);
  const data = graph.data;

  return (
    <div>
      <Topbar
        eyebrow="Threat Annotated Instruction Graph"
        title="TAIG"
        right={<Pill tone="acid"><span className="live-dot mr-1" />Live view</Pill>}
      />
      <div className="p-6 max-w-[1600px]">
        <Panel>
          <PanelHeader
            eyebrow="Permissions · classes · methods · IOCs"
            title="Instruction graph"
            right={
              <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-ink/50">
                <span>{data?.nodes.length ?? 0} nodes</span><span>·</span><span>{data?.edges.length ?? 0} edges</span>
              </div>
            }
          />
          <div className="p-4 min-h-[400px]">
            {graph.loading ? (
              <div className="h-[620px] flex items-center justify-center font-mono text-xs text-ink/50 gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Building graph…
              </div>
            ) : !data || data.nodes.length === 0 ? (
              <div className="h-[400px] flex items-center justify-center font-mono text-xs text-ink/50">No graph data yet.</div>
            ) : (
              <TAIGGraph nodes={data.nodes} edges={data.edges} height={620} />
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
