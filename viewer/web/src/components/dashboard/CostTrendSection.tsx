import { useMemo, type JSX } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";

import { buildDashboardCostTrend } from "@/lib/dashboard-data";
import { formatCost } from "@/lib/dashboard-stats";
import type { RecordSummary } from "@/lib/types";
import {
  ChartContainer,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const WINDOW_OPTIONS = [1, 3, 7, 14, 30] as const;

const AXIS_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

const TOOLTIP_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

type CostTrendSectionProps = {
  records: RecordSummary[];
  rollingWindowDays: number;
  onRollingWindowDaysChange: (value: number) => void;
};

function formatDelta(deltaUsd: number | null, deltaPct: number | null): string {
  if (deltaUsd == null || deltaPct == null) return "—";
  const prefix = deltaUsd > 0 ? "+" : "";
  return `${prefix}${formatCost(deltaUsd)} (${prefix}${deltaPct.toFixed(1)}%)`;
}

function formatAxisCost(value: number): string {
  if (value <= 0) return "$0";
  if (value < 0.1) return `$${value.toFixed(2)}`;
  if (value < 1) return `$${value.toFixed(1)}`;
  return `$${value.toFixed(0)}`;
}

function CostTrendTooltip({
  active,
  payload,
}: TooltipProps<number, string> & {
  payload?: Array<{
    payload?: {
      dayStartMs?: number;
      recordCount?: number;
      dailyAverageCostUsd?: number | null;
      rollingAverageCostUsd?: number | null;
    };
  }>;
}): JSX.Element | null {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0]?.payload;
  if (!point || point.dayStartMs == null) return null;

  return (
    <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-3 py-2 shadow-md">
      <div className="text-[11px] font-medium text-[var(--text-primary)]">
        {TOOLTIP_DATE_FORMATTER.format(point.dayStartMs)}
      </div>
      <div className="mt-1 space-y-0.5 text-[10px] text-[var(--text-tertiary)]">
        <div>Records: {point.recordCount ?? 0}</div>
        <div>Daily avg: {formatCost(point.dailyAverageCostUsd ?? null)}</div>
        <div>Rolling avg: {formatCost(point.rollingAverageCostUsd ?? null)}</div>
      </div>
    </div>
  );
}

export function CostTrendSection({
  records,
  rollingWindowDays,
  onRollingWindowDaysChange,
}: CostTrendSectionProps): JSX.Element {
  const trend = useMemo(
    () => buildDashboardCostTrend(records, rollingWindowDays),
    [records, rollingWindowDays],
  );

  const chartConfig = useMemo<ChartConfig>(
    () => ({
      rollingAverageCostUsd: {
        label: "Rolling average",
        color: "var(--accent)",
      },
      recordCount: {
        label: "Record count",
        color: "var(--border-subtle)",
      },
    }),
    [],
  );

  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
          Cost Trend
        </h2>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-[var(--text-quaternary)]">Window</span>
          <Select
            value={String(rollingWindowDays)}
            onValueChange={(value) => onRollingWindowDaysChange(Number(value))}
          >
            <SelectTrigger size="sm" className="h-6">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WINDOW_OPTIONS.map((windowDays) => (
                <SelectItem key={windowDays} value={String(windowDays)}>
                  {windowDays}d
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] p-4">
        {trend.points.length === 0 ? (
          <div className="py-8 text-center text-[11px] text-[var(--text-quaternary)]">
            No cost data matches the current filters
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-baseline gap-6">
              <div>
                <p className="text-[10px] uppercase tracking-[0.06em] text-[var(--text-quaternary)]">
                  {rollingWindowDays}d avg
                </p>
                <p className="mt-0.5 font-mono text-[18px] font-medium leading-tight text-[var(--text-primary)]">
                  {formatCost(trend.latestAverageCostUsd)}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.06em] text-[var(--text-quaternary)]">
                  vs prev {rollingWindowDays}d
                </p>
                <p className="mt-0.5 font-mono text-[12px] leading-tight text-[var(--text-tertiary)]">
                  {formatDelta(trend.deltaUsd, trend.deltaPct)}
                </p>
              </div>
            </div>

            <ChartContainer config={chartConfig} className="h-[220px] w-full">
              <ComposedChart
                data={trend.points}
                margin={{ top: 4, right: 8, bottom: 4, left: 8 }}
              >
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis
                  dataKey="dayStartMs"
                  minTickGap={28}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => AXIS_DATE_FORMATTER.format(new Date(value))}
                />
                <YAxis
                  yAxisId="cost"
                  tickLine={false}
                  axisLine={false}
                  width={44}
                  tickFormatter={formatAxisCost}
                />
                <YAxis yAxisId="count" orientation="right" hide />
                <Tooltip cursor={false} content={<CostTrendTooltip />} />
                <Bar
                  yAxisId="count"
                  dataKey="recordCount"
                  fill="var(--color-recordCount)"
                  fillOpacity={0.5}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={16}
                />
                <Line
                  yAxisId="cost"
                  type="monotone"
                  dataKey="rollingAverageCostUsd"
                  stroke="var(--color-rollingAverageCostUsd)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 3, fill: "var(--accent)", strokeWidth: 0 }}
                />
              </ComposedChart>
            </ChartContainer>
          </>
        )}
      </div>
    </section>
  );
}
