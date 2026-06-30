import { useEffect, useRef, useState, type JSX } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Sparkles } from "lucide-react";

import {
  createGenerationTask,
  fetchGenerationOptions,
  fetchGenerationStatus,
} from "@/lib/api";
import { useViewerDispatch } from "@/lib/viewer-context";
import { viewerQueryKeys } from "@/lib/viewer-queries";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const THINKING_LABELS: Record<string, string> = {
  low: "Low",
  med: "Medium",
  high: "High",
  xhigh: "Extra high",
};

const FIELD_CLASS =
  "h-8 w-full min-w-0 rounded-md border border-[var(--border-default)] bg-[var(--surface-0)] px-2.5 py-1.5 text-[12px] text-[var(--text-primary)] outline-none transition-all duration-150 placeholder:text-[var(--text-quaternary)] focus-visible:border-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--accent-soft)]";

type NewTaskDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function NewTaskDialog({ open, onOpenChange }: NewTaskDialogProps): JSX.Element {
  const dispatch = useViewerDispatch();
  const queryClient = useQueryClient();

  const optionsQuery = useQuery({
    queryKey: ["generation-options"],
    queryFn: fetchGenerationOptions,
    staleTime: 30_000,
  });
  const statusQuery = useQuery({
    queryKey: ["generation-status"],
    queryFn: fetchGenerationStatus,
    enabled: open,
    refetchInterval: open ? 2_500 : false,
  });

  const options = optionsQuery.data ?? null;

  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [thinking, setThinking] = useState("high");
  const [maxCost, setMaxCost] = useState("3");
  const [prompt, setPrompt] = useState("");
  const initializedRef = useRef(false);

  useEffect(() => {
    if (!options || initializedRef.current) {
      return;
    }
    const chosen = options.providers.find((p) => p.available) ?? options.providers[0];
    if (!chosen) {
      return;
    }
    initializedRef.current = true;
    setProvider(chosen.value);
    setModel(chosen.default_model);
    setThinking(options.default_thinking_level);
    setMaxCost(String(options.default_max_cost_usd));
  }, [options]);

  const selectedProvider = options?.providers.find((p) => p.value === provider) ?? null;
  const hasAvailableProvider = (options?.providers ?? []).some((p) => p.available);

  const handleProviderChange = (value: string) => {
    setProvider(value);
    const next = options?.providers.find((p) => p.value === value);
    if (next) {
      setModel(next.default_model);
    }
  };

  const mutation = useMutation({
    mutationFn: createGenerationTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: viewerQueryKeys.stagingEntries() });
      queryClient.invalidateQueries({ queryKey: ["generation-status"] });
      queryClient.invalidateQueries({ queryKey: ["generation-log"] });
      dispatch({ type: "SET_BROWSER_TAB", payload: "staging" });
      setPrompt("");
      onOpenChange(false);
    },
  });

  const runningCount = statusQuery.data?.running_count ?? 0;
  const maxConcurrent = statusQuery.data?.max_concurrent ?? 20;
  const atLimit = runningCount >= maxConcurrent;
  const canSubmit =
    prompt.trim().length > 0 &&
    provider.length > 0 &&
    model.trim().length > 0 &&
    !mutation.isPending &&
    !atLimit;

  const handleSubmit = () => {
    if (!canSubmit) {
      return;
    }
    const cost = Number(maxCost);
    mutation.mutate({
      prompt: prompt.trim(),
      provider,
      model: model.trim(),
      thinking_level: thinking,
      max_cost_usd: Number.isFinite(cost) && cost > 0 ? cost : null,
    });
  };

  const errorMessage = mutation.error instanceof Error ? mutation.error.message : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[460px]">
        <DialogHeader>
          <DialogTitle>New generation task</DialogTitle>
          <DialogDescription>
            Describe an articulated object and run a generation. Live progress shows up in the
            Staging tab.
          </DialogDescription>
        </DialogHeader>

        {atLimit ? (
          <div className="rounded-md border border-amber-500/20 bg-amber-500/[0.06] px-3 py-2 text-[11px] text-amber-600">
            Concurrency limit reached ({maxConcurrent} tasks running). Wait for one to finish before
            starting another.
          </div>
        ) : runningCount > 0 ? (
          <div className="rounded-md border border-[var(--border-default)] bg-[var(--surface-1)] px-3 py-2 text-[11px] text-[var(--text-secondary)]">
            {runningCount} task{runningCount === 1 ? "" : "s"} running ({runningCount}/{maxConcurrent}).
            You can queue another below.
          </div>
        ) : null}

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="task-prompt" className="text-[11px]">
              Prompt
            </Label>
            <textarea
              id="task-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={3}
              placeholder="an articulated desk lamp with a weighted base, a two-segment arm…"
              className={cn(FIELD_CLASS, "h-auto resize-y leading-5")}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-[11px]">Provider</Label>
              <Select value={provider} onValueChange={handleProviderChange}>
                <SelectTrigger className="h-8 w-full text-[11px]">
                  <SelectValue placeholder="Provider" />
                </SelectTrigger>
                <SelectContent>
                  {options?.providers.map((p) => (
                    <SelectItem key={p.value} value={p.value} disabled={!p.available}>
                      {p.label}
                      {p.available ? "" : " · no key"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="task-model" className="text-[11px]">
                Model
              </Label>
              <input
                id="task-model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                list="generation-model-options"
                placeholder="model id"
                className={FIELD_CLASS}
              />
              <datalist id="generation-model-options">
                {selectedProvider?.models.map((m) => <option key={m} value={m} />)}
              </datalist>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-[11px]">Thinking</Label>
              <Select value={thinking} onValueChange={setThinking}>
                <SelectTrigger className="h-8 w-full text-[11px]">
                  <SelectValue placeholder="Thinking" />
                </SelectTrigger>
                <SelectContent>
                  {(options?.thinking_levels ?? ["low", "med", "high", "xhigh"]).map((level) => (
                    <SelectItem key={level} value={level}>
                      {THINKING_LABELS[level] ?? level}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="task-cost" className="text-[11px]">
                Max cost (USD)
              </Label>
              <Input
                id="task-cost"
                type="number"
                min="0"
                step="0.5"
                value={maxCost}
                onChange={(event) => setMaxCost(event.target.value)}
              />
            </div>
          </div>

          {errorMessage ? (
            <p className="text-[11px] text-[var(--destructive)]">{errorMessage}</p>
          ) : null}
          {options && !hasAvailableProvider ? (
            <p className="text-[11px] text-[var(--text-tertiary)]">
              No provider API keys detected in .env. Configure a key to enable generation.
            </p>
          ) : null}
        </div>

        <div className="mt-1 flex items-center justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button size="sm" className="gap-1.5" onClick={handleSubmit} disabled={!canSubmit}>
            {mutation.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Sparkles className="size-3.5" />
            )}
            Create task
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
