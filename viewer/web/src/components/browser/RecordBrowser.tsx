import { useCallback, useEffect, useState, type JSX } from "react";

import type { SourceFilter } from "@/lib/types";
import { useViewer, useViewerDispatch } from "@/lib/viewer-context";
import { BulkActionBar } from "@/components/browser/BulkActionBar";
import { ExplorerFilters } from "@/components/browser/ExplorerFilters";
import { RecordSearch } from "@/components/browser/RecordSearch";
import { RecordList } from "@/components/browser/RecordList";
import { StagingList } from "@/components/browser/StagingList";

type BrowserTab = SourceFilter | "staging";

export function RecordBrowser(): JSX.Element {
  const { sourceFilter, loading, error, selection, multiSelection } = useViewer();
  const dispatch = useViewerDispatch();
  const [activeTab, setActiveTab] = useState<BrowserTab>(sourceFilter);
  const [visibleRecordIds, setVisibleRecordIds] = useState<string[]>([]);
  const handleVisibleIdsChange = useCallback((ids: string[]) => setVisibleRecordIds(ids), []);
  useEffect(() => {
    if (selection?.kind === "staging") {
      setActiveTab("staging");
      return;
    }
    setActiveTab(sourceFilter);
  }, [selection, sourceFilter]);

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col">
      <div className="flex items-center border-b border-[var(--border-default)] px-4">
        <div className="flex gap-0">
          <button
            type="button"
            onClick={() => {
              dispatch({ type: "SET_SOURCE_FILTER", payload: "workbench" });
              setActiveTab("workbench");
            }}
            className={`relative px-3 py-3 text-[11px] font-medium tracking-[0.01em] transition-colors duration-150 ${
              activeTab === "workbench"
                ? "text-[var(--text-primary)] after:absolute after:bottom-0 after:left-3 after:right-3 after:h-[1.5px] after:rounded-full after:bg-[var(--text-primary)]"
                : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
            }`}
          >
            Workbench
          </button>
          <button
            type="button"
            onClick={() => {
              dispatch({ type: "SET_SOURCE_FILTER", payload: "dataset" });
              setActiveTab("dataset");
            }}
            className={`relative px-3 py-3 text-[11px] font-medium tracking-[0.01em] transition-colors duration-150 ${
              activeTab === "dataset"
                ? "text-[var(--text-primary)] after:absolute after:bottom-0 after:left-3 after:right-3 after:h-[1.5px] after:rounded-full after:bg-[var(--text-primary)]"
                : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
            }`}
          >
            Dataset
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("staging")}
            className={`relative px-3 py-3 text-[11px] font-medium tracking-[0.01em] transition-colors duration-150 ${
              activeTab === "staging"
                ? "text-[var(--success)] after:absolute after:bottom-0 after:left-3 after:right-3 after:h-[1.5px] after:rounded-full after:bg-[var(--success)]"
                : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
            }`}
          >
            Staging
          </button>
        </div>
      </div>

      {error ? (
        <div className="border-b border-[rgba(209,52,21,0.1)] bg-[rgba(209,52,21,0.04)] px-4 py-2">
          <p className="text-[11px] text-[var(--destructive)]">{error}</p>
        </div>
      ) : null}

      {activeTab === "staging" ? (
        <>
          <div className="space-y-2 border-b border-[var(--border-default)] px-3 py-3">
            <RecordSearch placeholder="Search staging objects…" />
          </div>
          <StagingList />
        </>
      ) : (
        <>
          <div className="space-y-2 px-3 py-3">
            <RecordSearch placeholder="Search records…" />
            <ExplorerFilters />
          </div>

          {loading ? (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-[11px] text-[var(--text-quaternary)]">Loading…</p>
            </div>
          ) : (
            <>
              <RecordList onVisibleIdsChange={handleVisibleIdsChange} />
              {multiSelection.size > 0 ? (
                <BulkActionBar visibleRecordIds={visibleRecordIds} />
              ) : null}
            </>
          )}
        </>
      )}
    </div>
  );
}
