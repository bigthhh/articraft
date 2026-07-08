import { useCallback, useRef, useState, type JSX } from "react";
import { Loader2, ShieldAlert, ShieldCheck, ShieldX, Upload } from "lucide-react";

import { verifyBundle, type BundleVerifyResult } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type StatusTone = "good" | "warn" | "bad";

const TONE_STYLES: Record<StatusTone, string> = {
  good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700",
  warn: "border-amber-500/30 bg-amber-500/10 text-amber-700",
  bad: "border-red-500/30 bg-red-500/10 text-red-700",
};

function deriveStatus(result: BundleVerifyResult): {
  tone: StatusTone;
  Icon: typeof ShieldCheck;
  title: string;
  detail: string;
} {
  if (!result.valid) {
    return {
      tone: "bad",
      Icon: ShieldX,
      title: "无效或已被篡改",
      detail: result.reason ?? "签名或文件完整性校验未通过。",
    };
  }
  if (result.is_own) {
    return {
      tone: "good",
      Icon: ShieldCheck,
      title: "本项目产出 · 未被篡改",
      detail: "签名由本实例私钥签发，且所有文件与清单哈希一致。",
    };
  }
  return {
    tone: "warn",
    Icon: ShieldAlert,
    title: "签名有效、未被篡改，但公钥非本实例",
    detail: "内容可信，但签名公钥与当前实例不同（可能来自另一部署实例）。",
  };
}

export function VerifyBundleDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}): JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [result, setResult] = useState<BundleVerifyResult | null>(null);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setFileName(null);
    setResult(null);
  }, []);

  const runVerify = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setFileName(file.name);
    try {
      setResult(await verifyBundle(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "校验失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const handlePick = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) void runVerify(file);
      event.target.value = "";
    },
    [runVerify],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      event.preventDefault();
      const file = event.dataTransfer.files?.[0];
      if (file) void runVerify(file);
    },
    [runVerify],
  );

  const status = result ? deriveStatus(result) : null;
  const manifest = result?.manifest ?? null;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>校验 .artcraft 产出包</DialogTitle>
          <DialogDescription>确认文件是否由本项目签名、且未被篡改。</DialogDescription>
        </DialogHeader>

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          className="flex w-full flex-col items-center gap-2 rounded-lg border border-dashed border-[var(--border-strong)] bg-[var(--surface-1)] px-4 py-6 text-[12px] text-[var(--text-tertiary)] transition hover:border-[var(--border-default)] hover:text-[var(--text-secondary)]"
        >
          <Upload className="size-5 opacity-70" />
          <span>{fileName ? fileName : "点击选择，或拖入 .artcraft 文件"}</span>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".artcraft,application/zip"
          className="hidden"
          onChange={handlePick}
        />

        {loading ? (
          <div className="flex items-center gap-2 text-[12px] text-[var(--text-tertiary)]">
            <Loader2 className="size-4 animate-spin" /> 校验中…
          </div>
        ) : null}

        {error ? (
          <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-[12px] text-red-700">
            {error}
          </p>
        ) : null}

        {status ? (
          <div className={`rounded-lg border px-3 py-3 ${TONE_STYLES[status.tone]}`}>
            <div className="flex items-center gap-2 text-[13px] font-semibold">
              <status.Icon className="size-4 shrink-0" />
              {status.title}
            </div>
            <p className="mt-1 text-[11px] opacity-90">{status.detail}</p>
          </div>
        ) : null}

        {manifest ? (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px] text-[var(--text-secondary)]">
            <dt className="text-[var(--text-quaternary)]">Record</dt>
            <dd className="truncate font-mono">{manifest.record_id ?? "—"}</dd>
            <dt className="text-[var(--text-quaternary)]">Provider / Model</dt>
            <dd className="truncate">
              {manifest.provider ?? "—"} · {manifest.model_id ?? "—"}
            </dd>
            <dt className="text-[var(--text-quaternary)]">Exported</dt>
            <dd className="truncate">{manifest.exported_at ?? "—"}</dd>
            <dt className="text-[var(--text-quaternary)]">Files</dt>
            <dd>{manifest.files?.length ?? 0}</dd>
          </dl>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
