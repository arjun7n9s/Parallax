import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Compass, Maximize2, Network } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Pill } from "../components/primitives/Pill";
import { TAIGGraph } from "../components/primitives/Graph";
import { getTAIGGraph } from "../lib/api";
import type { TAIGNodes } from "../lib/mock-data";

export default function TAIG() {
  const [data, setData] = useState<TAIGNodes | null>(null);

  useEffect(() => {
    void (async () => setData(await getTAIGGraph("sub_0001")))();
  }, []);

  return (
    <div>
      <Topbar
        eyebrow="Threat Annotated Instruction Graph"
        title="TAIG"
        right={
          <Pill tone="acid">
            <span className="live-dot mr-1" />
            Live view
          </Pill>
        }
      />
      <div className="p-6 max-w-[1600px]">
        <Panel>
          <PanelHeader
            eyebrow="Aggregated across 1,247 submissions"
            title="Global TAIG"
            right={
              <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-ink/50">
                <span>{data?.nodes.length ?? 0} nodes</span>
                <span>·</span>
                <span>{data?.edges.length ?? 0} edges</span>
              </div>
            }
          />
          <div className="p-4">
            {data && (
              <TAIGGraph nodes={data.nodes} edges={data.edges} height={620} />
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}