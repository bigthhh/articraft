import { useState, useMemo, type JSX } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";

import { formatCost } from "@/lib/dashboard-stats";
import { formatCategoryLabel } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type CategoriesSectionProps = {
  categoryStats: Record<
    string,
    {
      count: number;
      average_rating: number | null;
      average_cost_usd: number | null;
    }
  >;
};

type SortKey = "category" | "count" | "average_rating" | "average_cost_usd";
type SortDirection = "asc" | "desc";

function formatAverageRating(value: number | null): string {
  return value != null ? `${value.toFixed(1)}★` : "—";
}

export function CategoriesSection({ categoryStats }: CategoriesSectionProps): JSX.Element | null {
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("count");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const allSorted = useMemo(
    () =>
      Object.entries(categoryStats).sort((left, right) => {
        const [leftCategory, leftStats] = left;
        const [rightCategory, rightStats] = right;
        const leftCategoryLabel = formatCategoryLabel(leftCategory);
        const rightCategoryLabel = formatCategoryLabel(rightCategory);

        const categoryFallback = leftCategoryLabel.localeCompare(rightCategoryLabel);

        if (sortKey === "category") {
          return sortDirection === "asc" ? categoryFallback : -categoryFallback;
        }

        const leftValue = leftStats[sortKey];
        const rightValue = rightStats[sortKey];

        if (leftValue == null && rightValue == null) return categoryFallback;
        if (leftValue == null) return 1;
        if (rightValue == null) return -1;

        const numericDelta = leftValue - rightValue;
        if (numericDelta === 0) return categoryFallback;
        return sortDirection === "asc" ? numericDelta : -numericDelta;
      }),
    [categoryStats, sortDirection, sortKey],
  );

  if (allSorted.length === 0) return null;

  const needle = filter.trim().toLowerCase();
  const filtered = needle
    ? allSorted.filter(([category]) => formatCategoryLabel(category).toLowerCase().includes(needle))
    : allSorted;

  function toggleSort(nextSortKey: SortKey): void {
    if (nextSortKey === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextSortKey);
    setSortDirection(nextSortKey === "category" ? "asc" : "desc");
  }

  function SortIndicator({ column }: { column: SortKey }): JSX.Element {
    if (sortKey !== column) {
      return <ArrowUpDown className="size-3 text-[var(--text-quaternary)]" />;
    }
    if (sortDirection === "asc") {
      return <ArrowUp className="size-3 text-[var(--text-tertiary)]" />;
    }
    return <ArrowDown className="size-3 text-[var(--text-tertiary)]" />;
  }

  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[10px] font-medium uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
          Categories
        </h2>
        <span className="text-[10px] tabular-nums text-[var(--text-quaternary)]">
          {filtered.length === allSorted.length
            ? `${allSorted.length}`
            : `${filtered.length} / ${allSorted.length}`}
        </span>
      </div>
      <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-0)]">
        {allSorted.length > 12 ? (
          <div className="flex items-center gap-2 border-b border-[var(--border-default)] px-3 py-1.5">
            <Search className="size-3 shrink-0 text-[var(--text-quaternary)]" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter categories..."
              className="h-6 w-full bg-transparent text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-quaternary)] focus:outline-none"
            />
          </div>
        ) : null}
        <div className="custom-scrollbar max-h-[320px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-4 py-3">
              <span className="text-[11px] text-[var(--text-quaternary)]">No matching categories</span>
            </div>
          ) : (
            <Table className="text-[11px]">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="h-8 px-4 py-[5px] text-[10px] uppercase tracking-[0.06em] text-[var(--text-quaternary)]">
                    <button
                      type="button"
                      onClick={() => toggleSort("category")}
                      className="flex items-center gap-1 text-left"
                    >
                      <span>Category</span>
                      <SortIndicator column="category" />
                    </button>
                  </TableHead>
                  <TableHead className="h-8 whitespace-nowrap px-4 py-[5px] text-right text-[10px] uppercase tracking-[0.06em] text-[var(--text-quaternary)]">
                    <button
                      type="button"
                      onClick={() => toggleSort("count")}
                      className="ml-auto flex items-center gap-1"
                    >
                      <span>Count</span>
                      <SortIndicator column="count" />
                    </button>
                  </TableHead>
                  <TableHead className="h-8 whitespace-nowrap px-4 py-[5px] text-right text-[10px] uppercase tracking-[0.06em] text-[var(--text-quaternary)]">
                    <button
                      type="button"
                      onClick={() => toggleSort("average_rating")}
                      className="ml-auto flex items-center gap-1"
                    >
                      <span>Avg Stars</span>
                      <SortIndicator column="average_rating" />
                    </button>
                  </TableHead>
                  <TableHead className="h-8 whitespace-nowrap px-4 py-[5px] text-right text-[10px] uppercase tracking-[0.06em] text-[var(--text-quaternary)]">
                    <button
                      type="button"
                      onClick={() => toggleSort("average_cost_usd")}
                      className="ml-auto flex items-center gap-1"
                    >
                      <span>Avg Cost</span>
                      <SortIndicator column="average_cost_usd" />
                    </button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map(([category, stats]) => (
                  <TableRow
                    key={category}
                    className="border-b border-[var(--border-subtle)] hover:bg-[var(--surface-1)]"
                  >
                    <TableCell className="w-full px-4 py-[5px] text-[var(--text-secondary)]">
                      {formatCategoryLabel(category)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-4 py-[5px] text-right font-mono tabular-nums text-[var(--text-tertiary)]">
                      {stats.count}
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-4 py-[5px] text-right font-mono tabular-nums text-[var(--text-tertiary)]">
                      {formatAverageRating(stats.average_rating)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-4 py-[5px] text-right font-mono tabular-nums text-[var(--text-tertiary)]">
                      {formatCost(stats.average_cost_usd)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </section>
  );
}
