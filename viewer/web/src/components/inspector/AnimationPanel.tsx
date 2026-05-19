import { useEffect, useState, type JSX } from "react";
import { Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";

import { fetchRecordAnimation, fetchRecordTurnAnimation } from "@/lib/api";
import type { RecordAnimation } from "@/lib/types";
import { useViewer } from "@/lib/viewer-context";
import { useAnimation } from "@/lib/animation-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { codeTheme, SyntaxHighlighter } from "@/components/inspector/syntax-highlighting";

const FRAME_MS = 500;
const ANIMATION_MODE = import.meta.env.VITE_ANIMATION_MODE === "turn" ? "turn" : "primitive";
const SUMMARY_SECTION_NAMES = new Set([
  "Tool calls",
  "Reads",
  "Read snippets",
  "Writes",
  "Write snippets",
  "Validations",
  "Results",
  "Tool outcomes",
]);

type TurnSummarySection = {
  title: string;
  items: string[];
};

type ParsedTurnSummary = {
  headline: string;
  sections: TurnSummarySection[];
};

type SectionItemGroup =
  | { kind: "text"; text: string }
  | { kind: "snippet"; title: string; lines: string[] };

function formatChangeLabel(toolName: string, traceLine: number): string {
  return `${toolName} · trace line ${traceLine}`;
}

function formatFrameStatus(status: string): string | null {
  return status === "fallback" ? "fallback" : null;
}

function parseTurnSummary(value: string): ParsedTurnSummary {
  const lines = value.split(/\r?\n/);
  const headlineLines: string[] = [];
  const sections: TurnSummarySection[] = [];
  let current: TurnSummarySection | null = null;

  for (const line of lines) {
    const trimmed = line.trim();
    const maybeTitle = trimmed.endsWith(":") ? trimmed.slice(0, -1) : "";
    if (SUMMARY_SECTION_NAMES.has(maybeTitle)) {
      current = { title: maybeTitle, items: [] };
      sections.push(current);
      continue;
    }
    if (current) {
      if (trimmed.startsWith("- ")) {
        current.items.push(trimmed.slice(2));
      } else if (trimmed) {
        current.items.push(trimmed);
      }
      continue;
    }
    if (trimmed) {
      headlineLines.push(trimmed);
    }
  }

  return {
    headline: headlineLines.join(" ") || "Agent turn",
    sections: sections.filter((section) => section.items.length > 0),
  };
}

function sectionItems(parsed: ParsedTurnSummary, title: string): string[] {
  return parsed.sections.find((section) => section.title === title)?.items ?? [];
}

function isSnippetLine(value: string): boolean {
  return value.startsWith("    ");
}

function groupSectionItems(items: string[]): SectionItemGroup[] {
  const groups: SectionItemGroup[] = [];
  let currentSnippet: { kind: "snippet"; title: string; lines: string[] } | null = null;

  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    if (isSnippetLine(item)) {
      if (!currentSnippet) {
        currentSnippet = { kind: "snippet", title: "snippet", lines: [] };
        groups.push(currentSnippet);
      }
      currentSnippet.lines.push(item.slice(4));
      continue;
    }

    currentSnippet = null;
    const nextItem = items[index + 1];
    if (nextItem && isSnippetLine(nextItem)) {
      currentSnippet = { kind: "snippet", title: item, lines: [] };
      groups.push(currentSnippet);
    } else {
      groups.push({ kind: "text", text: item });
    }
  }

  return groups;
}

function sectionTone(title: string): string {
  if (title.startsWith("Read")) return "border-sky-500/30 bg-sky-500/10";
  if (title.startsWith("Write")) return "border-emerald-500/30 bg-emerald-500/10";
  if (title === "Validations") return "border-violet-500/30 bg-violet-500/10";
  if (title === "Results" || title === "Tool outcomes") return "border-amber-500/30 bg-amber-500/10";
  return "border-[var(--border-default)] bg-[var(--surface-0)]";
}

function itemTone(item: string): string {
  if (item.startsWith("passed:")) return "border-emerald-500/30 bg-emerald-500/10";
  if (item.startsWith("failed:")) return "border-rose-500/30 bg-rose-500/10";
  if (item.startsWith("pending:")) return "border-amber-500/30 bg-amber-500/10";
  return "";
}

function snippetLineClass(line: string): string {
  if (line.startsWith("+") && !line.startsWith("+++")) {
    return "bg-emerald-500/10 text-emerald-300";
  }
  if (line.startsWith("-") && !line.startsWith("---")) {
    return "bg-rose-500/10 text-rose-300";
  }
  return "text-[var(--text-secondary)]";
}

function InfoSection({ title, items }: { title: string; items: string[] }): JSX.Element | null {
  if (items.length === 0) return null;
  const groups = groupSectionItems(items);
  const tone = sectionTone(title);
  return (
    <div className="space-y-1.5">
      <div className="text-[12px] font-semibold uppercase tracking-wide text-[var(--text-quaternary)]">
        {title}
      </div>
      <div className="space-y-1">
        {groups.map((item, index) =>
          item.kind === "snippet" ? (
            <div key={`${title}-${index}`} className={`overflow-hidden rounded border ${tone}`}>
              <div className="border-b border-[var(--border-default)] px-2.5 py-1.5 font-mono text-[12px] text-[var(--text-tertiary)]">
                {item.title}
              </div>
              <pre className="overflow-x-auto px-2.5 py-1.5 font-mono text-[12px] leading-5">
                {item.lines.map((line, lineIndex) => (
                  <span
                    key={`${title}-${index}-${lineIndex}`}
                    className={`block min-h-5 whitespace-pre ${snippetLineClass(line)}`}
                  >
                    {line}
                  </span>
                ))}
              </pre>
            </div>
          ) : (
            <div
              key={`${title}-${index}`}
              className={`rounded border px-2.5 py-1.5 text-[13px] leading-6 text-[var(--text-secondary)] ${itemTone(item.text) || tone}`}
            >
              {item.text}
            </div>
          ),
        )}
      </div>
    </div>
  );
}

function TurnFrameCard({
  frame,
}: {
  frame: NonNullable<RecordAnimation["frames"][number]>;
}): JSX.Element {
  const parsed = parseTurnSummary(frame.code_snippet);
  const didSections = ["Reads", "Read snippets", "Writes", "Write snippets", "Validations"].map((title) => ({
    title,
    items: sectionItems(parsed, title),
  }));
  const outcomeSections = ["Results", "Tool outcomes"].map((title) => ({
    title,
    items: sectionItems(parsed, title),
  }));

  return (
    <div className="space-y-3 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded border border-[var(--accent-blue)] bg-[var(--accent-blue-muted)] px-2.5 py-1.5 font-mono text-[13px] font-semibold text-[var(--text-primary)]">
          Turn {frame.index}
        </span>
      </div>

      <div className="rounded border border-[var(--border-default)] bg-[var(--surface-1)] px-3 py-2.5 text-[14px] leading-6 text-[var(--text-primary)]">
        {parsed.headline}
      </div>

      <div className="min-h-0 space-y-4">
        <div className="space-y-2">
          <div className="text-[13px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
            Agent Did
          </div>
          {didSections.map((section) => (
            <InfoSection key={section.title} title={section.title} items={section.items} />
          ))}
        </div>
        <div className="space-y-2">
          <div className="text-[13px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
            Outcomes
          </div>
          {outcomeSections.map((section) => (
            <InfoSection key={section.title} title={section.title} items={section.items} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function AnimationPanel(): JSX.Element {
  const { selection } = useViewer();
  const { setActiveFrame } = useAnimation();
  const recordId = selection?.kind === "record" ? selection.recordId : null;
  const [animation, setAnimation] = useState<RecordAnimation | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setAnimation(null);
    setActiveIndex(0);
    setPlaying(false);
    setError(null);

    if (!recordId) {
      return;
    }

    setLoading(true);
    const fetchAnimation =
      ANIMATION_MODE === "turn" ? fetchRecordTurnAnimation : fetchRecordAnimation;

    fetchAnimation(recordId)
      .then((payload) => {
        if (cancelled) return;
        setAnimation(payload);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to build animation frames");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [recordId]);

  useEffect(() => {
    if (!playing || !animation || animation.frames.length <= 1) {
      return;
    }
    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % animation.frames.length);
    }, FRAME_MS);
    return () => window.clearInterval(timer);
  }, [animation, playing]);

  const frame = animation?.frames[activeIndex] ?? null;

  useEffect(() => {
    setActiveFrame(frame);
  }, [frame, setActiveFrame]);

  useEffect(() => {
    return () => setActiveFrame(null);
  }, [recordId, setActiveFrame]);

  if (!recordId) {
    return (
      <div className="flex h-32 items-center justify-center">
        <p className="text-[10px] text-[var(--text-quaternary)]">Animation is available for records</p>
      </div>
    );
  }

  if (loading && !animation) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-52 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-32 items-center justify-center">
        <p className="px-3 text-center text-[10px] text-[var(--text-quaternary)]">{error}</p>
      </div>
    );
  }

  if (!animation || animation.frames.length === 0 || !frame) {
    return (
      <div className="flex h-32 items-center justify-center">
        <p className="px-3 text-center text-[10px] text-[var(--text-quaternary)]">
          No animation frames detected in trace.
        </p>
      </div>
    );
  }

  const hasMultipleFrames = animation.frames.length > 1;
  const lastIndex = animation.frames.length - 1;
  const frameStatus = formatFrameStatus(frame.compile_status);

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex shrink-0 items-center gap-2 rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-2 py-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          aria-label="Restart"
          onClick={() => setActiveIndex(0)}
          disabled={!hasMultipleFrames}
        >
          <RotateCcw className="size-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          aria-label="Previous frame"
          onClick={() => setActiveIndex((c) => Math.max(0, c - 1))}
          disabled={!hasMultipleFrames}
        >
          <SkipBack className="size-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          aria-label={playing ? "Pause" : "Play"}
          onClick={() => setPlaying((v) => !v)}
          disabled={!hasMultipleFrames}
        >
          {playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          aria-label="Next frame"
          onClick={() => setActiveIndex((c) => Math.min(lastIndex, c + 1))}
          disabled={!hasMultipleFrames}
        >
          <SkipForward className="size-3.5" />
        </Button>
        <input
          type="range"
          min={0}
          max={lastIndex}
          value={activeIndex}
          onChange={(event) => setActiveIndex(Number(event.target.value))}
          className="min-w-0 flex-1"
          aria-label="Animation frame"
          disabled={!hasMultipleFrames}
        />
        <span className="w-14 text-right font-mono text-[10px] text-[var(--text-tertiary)]">
          {activeIndex + 1} / {animation.frames.length}
        </span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-[var(--border-default)] bg-[var(--surface-0)]">
        <div className="flex h-8 shrink-0 items-center border-b border-[var(--border-default)] px-3">
          <span className="font-mono text-[10px] text-[var(--text-tertiary)]">
            {formatChangeLabel(frame.tool_name, frame.trace_line)}
          </span>
          {frameStatus ? (
            <span
              className="ml-2 truncate text-[10px] text-[var(--text-quaternary)]"
              title={frame.compile_error ?? undefined}
            >
              {frameStatus}
            </span>
          ) : null}
          {animation.skipped_count > 0 ? (
            <span className="ml-auto text-[10px] text-[var(--text-quaternary)]">
              {animation.skipped_count} skipped
            </span>
          ) : null}
        </div>
        <div className="code-panel-scroll min-h-0 flex-1 overflow-auto">
          {frame.tool_name === "agent_turn" ? (
            <TurnFrameCard frame={frame} />
          ) : (
            <SyntaxHighlighter
              language="python"
              style={codeTheme}
              customStyle={{
                margin: 0,
                padding: "12px",
                background: "transparent",
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                lineHeight: "1.6",
                minWidth: "100%",
              }}
              codeTagProps={{
                style: {
                  fontFamily: "var(--font-mono)",
                  whiteSpace: "pre",
                },
              }}
            >
              {frame.code_snippet}
            </SyntaxHighlighter>
          )}
        </div>
      </div>
    </div>
  );
}
