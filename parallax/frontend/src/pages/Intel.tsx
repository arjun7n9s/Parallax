import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Compass, Eye, TrendingUp, Users2 } from "lucide-react";
import { Topbar } from "../components/layout/Topbar";
import { Panel, PanelHeader } from "../components/primitives/Panel";
import { Kpi } from "../components/primitives/Kpi";
import { Distribution } from "../components/primitives/Graph";
import { getKpi, getRecentFamilies } from "../lib/api";

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.04, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] },
  }),
};

export default function Intel() {
  const [kpi, setKpi] = useState<Awaited<ReturnType<typeof getKpi>> | null>(null);
  const [families, setFamilies] = useState<Awaited<ReturnType<typeof getRecentFamilies>>>([]);

  useEffect(() => {
    void (async () => {
      setKpi(await getKpi());
      setFamilies(await getRecentFamilies());
    })();
  }, []);

  return (
    <div>
      <Topbar eyebrow="Threat intelligence" title="Intel" />
      <div className="p-6 max-w-[1600px] space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-ink/20 border border-ink/10">
          <motion.div custom={0} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="Families tracked" value={kpi?.familiesTracked ?? 0} emphasis="bone" />
          </motion.div>
          <motion.div custom={1} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="New (7d)" value={kpi?.newFamilies ?? 0} emphasis="bone" delta={18} />
          </motion.div>
          <motion.div custom={2} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="IOCs (7d)" value={kpi?.iocsDiscovered ?? 0} emphasis="bone" delta={4} />
          </motion.div>
          <motion.div custom={3} initial="hidden" animate="show" variants={fadeUp}>
            <Kpi eyebrow="Calibration drift" value="0.03" unit="Brier" emphasis="acid" delta={-12} />
          </motion.div>
        </div>

        <motion.div custom={0} initial="hidden" animate="show" variants={fadeUp}>
          <Panel>
            <PanelHeader
              eyebrow="Last 7 days"
              title="Top families"
            />
            <div className="px-6 pb-6">
              <Distribution
                items={families.map((f, i) => ({
                  label: f.family,
                  value: f.count,
                  color: i === 0 ? "#7C1F2D" : i < 3 ? "#0A0A0A" : "#0A0A0A66",
                }))}
              />
            </div>
          </Panel>
        </motion.div>
      </div>
    </div>
  );
}