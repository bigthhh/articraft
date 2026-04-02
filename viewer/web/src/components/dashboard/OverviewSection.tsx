import type { JSX } from "react";

import type { DashboardOverviewStats } from "@/lib/dashboard-data";
import { formatBytes, formatCost } from "@/lib/dashboard-stats";
import { StatBox } from "@/components/dashboard/StatBox";

type OverviewSectionProps = {
  stats: DashboardOverviewStats;
};

export function OverviewSection({ stats }: OverviewSectionProps): JSX.Element {
  return (
    <section>
      <h2 className="mb-2 text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
        Overview
      </h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatBox
          label="Records"
          value={String(stats.totalRecords)}
          detail={`${stats.categoryCount} categor${stats.categoryCount !== 1 ? "ies" : "y"}${stats.isFiltered ? " in current view" : ""}`}
        />
        <StatBox
          label="Runs"
          value={String(stats.totalRuns)}
          detail={`${stats.modelCount} model${stats.modelCount !== 1 ? "s" : ""}, ${stats.sdkCount} SDK${stats.sdkCount !== 1 ? "s" : ""}`}
        />
        <StatBox
          label="Total Cost"
          value={formatCost(stats.totalCostUsd)}
          detail={
            stats.averageCostUsd != null
              ? `${formatCost(stats.averageCostUsd)} avg/record`
              : undefined
          }
        />
        <StatBox
          label="Data Size"
          value={stats.dataSizeBytes != null ? formatBytes(stats.dataSizeBytes) : "—"}
          detail={stats.dataSizeBytes != null ? "excl. gitignored" : undefined}
        />
      </div>
    </section>
  );
}
