import { useEffect, useRef, useState, type JSX } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Loader2, Terminal } from "lucide-react";

import { fetchGenerationLog } from "@/lib/api";

type TaskLogPanelProps = {
  runId: string | null;
};

export function TaskLogPanel({ runId }: TaskLogPanelProps): JSX.Element {
  const [collapsed, setCollapsed] = useState(false);
  const logQuery = useQuery({
    queryKey: ["generation-log", runId],
    queryFn: () => fetchGenerationLog(runId),
    enabled: runId != null,
    refetchInterval: (query) => (query.state.data?.running ? 1500 : false),
  });
  const data = runId != null ? logQuery.data : undefined;
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && !collapsed) {
      el.scrollTop = el.scrollHeight;
    }
  }, [data?.log, collapsed]);

  const running = data?.running ?? false;
  const failed = !running && data?.returncode != null && data.returncode !== 0;
  const succeeded = !running && data?.returncode === 0;

  const statusNode = running ? (
    <span className="inline-flex items-center gap-1 text-[var(--accent)]">
      <Loader2 className="size-3 animate-spin" /> Running
    </span>
  ) : failed ? (
    <span className="inline-flex items-center gap-1 text-[var(--destructive)]">
      <AlertTriangle className="size-3" /> Failed{data?.returncode != null ? ` (exit ${data.returncode})` : ""}
    </span>
  ) : succeeded ? (
    <span className="inline-flex items-center gap-1 text-emerald-600">
      <CheckCircle2 className="size-3" /> Done
    </span>
  ) : (
    <span className="text-[var(--text-quaternary)]">Idle</span>
  );

  return (
    <div className="flex shrink-0 flex-col border-t border-[var(--border-default)] bg-[var(--surface-0)]">
      <button
        type="button"
        onClick={() => setCollapsed((value) => !value)}
        className="flex h-8 shrink-0 items-center justify-between gap-2 px-3 text-[11px] font-medium text-[var(--text-secondary)] transition-colors duration-150 hover:bg-[var(--surface-1)]"
      >
        <span className="inline-flex items-center gap-1.5">
          <Terminal className="size-3.5 text-[var(--text-tertiary)]" />
          Task Log
        </span>
        <span className="inline-flex items-center gap-2">
          {statusNode}
          {collapsed ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </span>
      </button>

      {!collapsed ? (
        <div className="flex min-h-0 flex-col border-t border-[var(--border-subtle)]">
          {data?.prompt ? (
            <p className="truncate px-3 py-1 text-[10px] text-[var(--text-tertiary)]">
              {data.model ? `${data.model} · ` : ""}
              {data.prompt}
            </p>
          ) : null}
          <div ref={scrollRef} className="h-[240px] overflow-auto bg-[var(--surface-2)] px-3 py-2">
            {data?.has_log ? (
              <pre className="whitespace-pre-wrap break-words font-mono text-[10px] leading-[1.5] text-[var(--text-secondary)]">
                {data.truncated ? "…(earlier output truncated)\n" : ""}
                {data.log}
              </pre>
            ) : runId == null ? (
              <p className="text-[11px] text-[var(--text-quaternary)]">
                Select a task in the Staging list to view its live work log here — including full
                error output if it fails.
              </p>
            ) : (
              <p className="text-[11px] text-[var(--text-quaternary)]">
                No work log captured for this task yet.
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
