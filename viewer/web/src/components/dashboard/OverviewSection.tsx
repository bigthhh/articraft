import type { JSX } from "react";

import type { RepoStats } from "@/lib/types";
import { formatBytes, formatCost } from "@/lib/dashboard-stats";
import { StatBox } from "@/components/dashboard/StatBox";

type OverviewSectionProps = {
  stats: RepoStats;
};

export function OverviewSection({ stats }: OverviewSectionProps): JSX.Element {
  const modelCount = Object.keys(stats.model_counts).length;
  const categoryCount = Object.keys(stats.category_counts).length;
  const avgCost =
    stats.total_cost_usd != null && stats.total_records > 0
      ? stats.total_cost_usd / stats.total_records
      : null;

  return (
    <section>
      <h2 className="mb-2 text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
        Overview
      </h2>
      <div className="grid grid-cols-2 gap-2">
        <StatBox
          label="Records"
          value={String(stats.total_records)}
          detail={`${stats.workbench_count} workbench, ${stats.dataset_count} dataset`}
        />
        <StatBox
          label="Runs"
          value={String(stats.total_runs)}
          detail={`${modelCount} model${modelCount !== 1 ? "s" : ""}, ${categoryCount} categor${categoryCount !== 1 ? "ies" : "y"}`}
        />
        <StatBox
          label="Total Cost"
          value={formatCost(stats.total_cost_usd)}
          detail={avgCost != null ? `${formatCost(avgCost)} avg/record` : undefined}
        />
        <StatBox
          label="Data Size"
          value={stats.data_size_bytes != null ? formatBytes(stats.data_size_bytes) : "—"}
          detail={stats.data_size_bytes != null ? "excl. gitignored" : undefined}
        />
      </div>
    </section>
  );
}
