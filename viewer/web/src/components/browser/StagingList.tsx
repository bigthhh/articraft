import { useMemo, type JSX } from "react";

import type { StagingEntry, ViewerSelection } from "@/lib/types";
import { useViewer, useViewerDispatch } from "@/lib/viewer-context";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getPreviewStagingEntries,
  isPreviewStagingEntry,
} from "@/components/browser/staging-preview";

function truncateWithEllipsis(value: string, maxLength = 88): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

function formatTimeAgo(dateString: string | null): string | null {
  if (!dateString) return null;
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return null;

  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function statusDotClass(status: string | null): string {
  switch ((status ?? "").toLowerCase()) {
    case "failed":
      return "bg-[var(--destructive)]";
    case "success":
      return "bg-[var(--success)]";
    default:
      return "bg-[var(--success)] staging-pulse";
  }
}

function isRunningEntry(entry: StagingEntry): boolean {
  const status = (entry.status ?? "").toLowerCase();
  return status !== "failed" && status !== "success";
}

function isStagingSelected(selection: ViewerSelection | null, entry: StagingEntry): boolean {
  return (
    selection?.kind === "staging" &&
    selection.runId === entry.run_id &&
    selection.recordId === entry.record_id
  );
}

function matchesSearch(entry: StagingEntry, query: string): boolean {
  if (!query) {
    return true;
  }

  const haystack = [
    entry.title,
    entry.prompt_preview,
    entry.record_id,
    entry.run_id,
    entry.model_id,
    entry.provider,
    entry.status,
  ]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase();

  return haystack.includes(query.toLowerCase());
}

function StagingListItem({ entry }: { entry: StagingEntry }): JSX.Element {
  const { selection } = useViewer();
  const dispatch = useViewerDispatch();
  const isPreview = isPreviewStagingEntry(entry);
  const isSelected = isStagingSelected(selection, entry);
  const summaryText = truncateWithEllipsis(entry.prompt_preview || entry.title || "Untitled");
  const metadata = [
    entry.status,
    entry.model_id,
    entry.turn_count !== null ? `${entry.turn_count} turns` : null,
    formatTimeAgo(entry.updated_at),
  ].filter((value): value is string => Boolean(value));

  return (
    <div className="px-1.5">
      <div
        className={cn(
          "group flex items-start gap-0.5 rounded-lg px-2.5 py-2 transition-colors duration-100",
          isSelected ? "bg-[rgba(26,138,74,0.08)]" : "hover:bg-[var(--surface-1)]",
          isPreview && "border border-dashed border-[rgba(26,138,74,0.22)] bg-[rgba(26,138,74,0.04)]",
        )}
      >
        <button
          type="button"
          disabled={isPreview}
          onClick={() =>
            dispatch({
              type: "SELECT_ITEM",
              payload: { kind: "staging", runId: entry.run_id, recordId: entry.record_id },
            })
          }
          className="min-w-0 flex-1 rounded-sm py-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(26,138,74,0.18)] disabled:cursor-default"
          title={summaryText}
        >
          <div className="flex items-start gap-2">
            <span className={cn("mt-[5px] size-[6px] shrink-0 rounded-full", statusDotClass(entry.status))} />

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <p
                  className={cn(
                    "break-words text-[11px] leading-[1.45]",
                    isSelected ? "font-medium text-[var(--text-primary)]" : "text-[var(--text-secondary)]",
                    isPreview && "text-[var(--text-primary)]",
                  )}
                >
                  {summaryText}
                </p>
                {isPreview ? (
                  <span className="shrink-0 rounded-full border border-[rgba(26,138,74,0.22)] bg-[rgba(26,138,74,0.07)] px-1.5 py-0.5 text-[8.5px] font-medium uppercase tracking-[0.06em] text-[var(--success)]">
                    Preview
                  </span>
                ) : null}
              </div>

              {metadata.length > 0 ? (
                <div className="mt-1 flex flex-wrap items-center gap-x-1 gap-y-0.5 text-[9.5px] text-[var(--text-tertiary)]">
                  {metadata.map((item, index) => (
                    <span key={`${entry.run_id}-${entry.record_id}-${item}`} className="flex items-center gap-x-1">
                      {index > 0 ? <span className="text-[var(--border-strong)]">·</span> : null}
                      <span>{item}</span>
                    </span>
                  ))}
                </div>
              ) : null}

              <p className="mt-1 text-[9.5px] text-[var(--text-quaternary)]">
                {isPreview ? "Temporary UI-only preview row" : `run ${entry.run_id}`}
              </p>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}

export function StagingList(): JSX.Element {
  const { bootstrap, loading, searchQuery } = useViewer();

  const entries = useMemo(
    () => getPreviewStagingEntries((bootstrap?.staging_entries ?? []).filter(isRunningEntry)),
    [bootstrap],
  );
  const visibleEntries = useMemo(
    () => entries.filter((entry) => matchesSearch(entry, searchQuery.trim())),
    [entries, searchQuery],
  );

  if (!bootstrap && loading) {
    return (
      <div className="flex flex-1 items-center justify-center p-4">
        <p className="text-[11px] text-[var(--text-quaternary)]">Loading…</p>
      </div>
    );
  }

  if (visibleEntries.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-4">
        <p className="text-[11px] text-[var(--text-quaternary)]">
          {searchQuery ? "No matching staging objects" : "No staging objects"}
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="py-0.5">
        {visibleEntries.map((entry) => (
          <StagingListItem key={`${entry.run_id}:${entry.record_id}`} entry={entry} />
        ))}
      </div>
    </ScrollArea>
  );
}
