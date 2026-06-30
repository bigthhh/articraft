from __future__ import annotations

import asyncio
import os
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Optional

from pydantic import BaseModel, Field

from articraft.config import load_repo_env

# Model ids mirror agent/providers/*.py DEFAULT_*_MODEL constants. They are kept
# as plain strings so the lightweight viewer API process never imports the
# generation runtime (cadquery, provider SDKs). The model field stays editable
# in the UI, so Azure deployment names or newer model ids can still be entered.
_PROVIDER_CATALOG: list[dict[str, object]] = [
    {
        "value": "gemini",
        "label": "Gemini",
        "key_env_vars": ["GEMINI_API_KEYS", "GEMINI_API_KEY"],
        "models": ["gemini-3.5-flash", "gemini-3-flash-preview"],
    },
    {
        "value": "openai",
        "label": "OpenAI / Azure",
        "key_env_vars": ["OPENAI_API_KEY", "OPENAI_API_KEYS"],
        "models": ["gpt-5.5-2026-04-23", "gpt-5.5"],
    },
    {
        "value": "anthropic",
        "label": "Anthropic",
        "key_env_vars": ["ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS"],
        "models": ["claude-opus-4-7"],
    },
    {
        "value": "openrouter",
        "label": "OpenRouter",
        "key_env_vars": ["OPENROUTER_API_KEY", "OPENROUTER_API_KEYS"],
        "models": ["tencent/hy3-preview:free"],
    },
    {
        "value": "deepseek",
        "label": "DeepSeek",
        "key_env_vars": ["DEEPSEEK_API_KEY", "DEEPSEEK_API_KEYS"],
        "models": ["deepseek-v4-pro"],
    },
    {
        "value": "dashscope",
        "label": "DashScope",
        "key_env_vars": ["DASHSCOPE_API_KEY", "DASHSCOPE_API_KEYS"],
        "models": ["qwen3.6-flash"],
    },
]

THINKING_LEVELS = ["low", "med", "high", "xhigh"]
DEFAULT_THINKING_LEVEL = "high"
DEFAULT_MAX_COST_USD = 3.0
MAX_CONCURRENT_TASKS = 20
_LOG_TAIL_CHARS = 2000
_MAX_TRACKED_FINISHED = 50


class ProviderModelInfo(BaseModel):
    value: str
    label: str
    available: bool
    models: list[str]
    default_model: str


class GenerationOptionsResponse(BaseModel):
    providers: list[ProviderModelInfo]
    thinking_levels: list[str]
    default_provider: Optional[str]
    default_thinking_level: str
    default_max_cost_usd: float


class GenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=200)
    thinking_level: str = DEFAULT_THINKING_LEVEL
    max_cost_usd: Optional[float] = Field(default=None, gt=0)


class GenerationTaskStatus(BaseModel):
    run_id: Optional[str] = None
    running: bool
    prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    returncode: Optional[int] = None
    error: Optional[str] = None


class GenerationSummary(BaseModel):
    running_count: int
    max_concurrent: int
    running: list[GenerationTaskStatus]


class GenerationLogResponse(BaseModel):
    run_id: Optional[str] = None
    running: bool
    returncode: Optional[int] = None
    prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    has_log: bool = False
    truncated: bool = False
    log: str = ""


class GenerationBusyError(RuntimeError):
    """Raised when the concurrent-task limit is reached."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    token = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"run_{token}_{secrets.token_hex(4)}"


# Prefix → provider, used to route the configured ARTICRAFT_MODEL (e.g. an Azure
# deployment name like "gpt-5.5-1") to the right provider's defaults.
_MODEL_PROVIDER_PREFIXES: tuple[tuple[str, str], ...] = (
    ("gemini", "gemini"),
    ("claude", "anthropic"),
    ("deepseek", "deepseek"),
    ("qwen", "dashscope"),
    ("qwq", "dashscope"),
    ("gpt", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("chatgpt", "openai"),
)


def _infer_provider(model_id: str) -> Optional[str]:
    normalized = model_id.strip().lower()
    for prefix, provider in _MODEL_PROVIDER_PREFIXES:
        if normalized.startswith(prefix):
            return provider
    return None


def list_provider_options(repo_root: Path) -> GenerationOptionsResponse:
    """Detect which providers have credentials and return selectable options.

    When `ARTICRAFT_MODEL` is set (e.g. an Azure deployment name that the default
    catalog model would not match), surface it as the default for the provider it
    belongs to so the New Task form preselects a working model.
    """
    load_repo_env(repo_root)
    configured_model = os.environ.get("ARTICRAFT_MODEL", "").strip()
    configured_provider = _infer_provider(configured_model) if configured_model else None

    providers: list[ProviderModelInfo] = []
    for spec in _PROVIDER_CATALOG:
        key_env_vars = spec["key_env_vars"]
        assert isinstance(key_env_vars, list)
        available = any(os.environ.get(name, "").strip() for name in key_env_vars)
        models = [str(m) for m in spec["models"]]  # type: ignore[union-attr]
        default_model = models[0]
        if configured_model and configured_provider == spec["value"]:
            if configured_model not in models:
                models.insert(0, configured_model)
            default_model = configured_model
        providers.append(
            ProviderModelInfo(
                value=str(spec["value"]),
                label=str(spec["label"]),
                available=available,
                models=models,
                default_model=default_model,
            )
        )

    if configured_provider and any(
        p.value == configured_provider and p.available for p in providers
    ):
        default_provider = configured_provider
    else:
        default_provider = next((p.value for p in providers if p.available), None)

    return GenerationOptionsResponse(
        providers=providers,
        thinking_levels=THINKING_LEVELS,
        default_provider=default_provider,
        default_thinking_level=DEFAULT_THINKING_LEVEL,
        default_max_cost_usd=DEFAULT_MAX_COST_USD,
    )


def _tail_text(path: Path, limit: int = _LOG_TAIL_CHARS) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text:
        return None
    return text[-limit:]


@dataclass
class _Task:
    run_id: str
    proc: asyncio.subprocess.Process
    log_path: Path
    status: GenerationTaskStatus


class GenerationManager:
    """Runs `articraft generate` as background subprocesses, up to a concurrency
    cap. Each task is launched with a pre-assigned `--run-id` so its work log
    (`cache/viewer_tasks/<run_id>.log`) can be addressed by the same run id that
    appears in `/api/staging`, letting the UI show per-task logs.
    """

    def __init__(self, repo_root: Path, data_root: Path) -> None:
        self._repo_root = repo_root
        self._data_root = data_root
        self._tasks: dict[str, _Task] = {}
        self._lock = asyncio.Lock()

    def _running_count(self) -> int:
        return sum(1 for task in self._tasks.values() if task.proc.returncode is None)

    def _prune(self) -> None:
        finished = [
            (run_id, task)
            for run_id, task in self._tasks.items()
            if task.proc.returncode is not None
        ]
        if len(finished) <= _MAX_TRACKED_FINISHED:
            return
        finished.sort(key=lambda item: item[1].status.finished_at or "")
        for run_id, _ in finished[: len(finished) - _MAX_TRACKED_FINISHED]:
            del self._tasks[run_id]

    def summary(self) -> GenerationSummary:
        running = sorted(
            (task.status for task in self._tasks.values() if task.proc.returncode is None),
            key=lambda status: status.started_at or "",
        )
        return GenerationSummary(
            running_count=len(running),
            max_concurrent=MAX_CONCURRENT_TASKS,
            running=list(running),
        )

    def _log_path_for(self, run_id: str) -> Path:
        return self._data_root / "cache" / "viewer_tasks" / f"{run_id}.log"

    def log(self, run_id: Optional[str], tail_chars: int = 24000) -> GenerationLogResponse:
        task = self._tasks.get(run_id) if run_id else None
        log_path = task.log_path if task else (self._log_path_for(run_id) if run_id else None)

        text = ""
        truncated = False
        if log_path is not None:
            try:
                raw = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                raw = ""
            if len(raw) > tail_chars:
                text, truncated = raw[-tail_chars:], True
            else:
                text = raw

        if task is not None:
            status = task.status
            return GenerationLogResponse(
                run_id=run_id,
                running=status.running,
                returncode=status.returncode,
                prompt=status.prompt,
                provider=status.provider,
                model=status.model,
                started_at=status.started_at,
                finished_at=status.finished_at,
                has_log=bool(text.strip()),
                truncated=truncated,
                log=text,
            )
        return GenerationLogResponse(
            run_id=run_id,
            running=False,
            has_log=bool(text.strip()),
            truncated=truncated,
            log=text,
        )

    async def start(self, request: GenerationRequest) -> GenerationTaskStatus:
        async with self._lock:
            if self._running_count() >= MAX_CONCURRENT_TASKS:
                raise GenerationBusyError(
                    f"Concurrency limit reached ({MAX_CONCURRENT_TASKS} tasks running). "
                    "Wait for one to finish before starting another."
                )
            self._prune()

            run_id = _new_run_id()
            max_cost = (
                request.max_cost_usd if request.max_cost_usd is not None else DEFAULT_MAX_COST_USD
            )
            cmd = [
                sys.executable,
                "-m",
                "cli.main",
                "generate",
                request.prompt,
                "--repo-root",
                str(self._repo_root),
                "--run-id",
                run_id,
                "--provider",
                request.provider,
                "--model",
                request.model,
                "--thinking",
                request.thinking_level,
                "--max-cost-usd",
                str(max_cost),
            ]
            if self._data_root is not None:
                cmd += ["--data-dir", str(self._data_root)]

            log_path = self._log_path_for(run_id)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = log_path.open("wb")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self._repo_root),
                stdout=log_file,
                stderr=asyncio.subprocess.STDOUT,
            )
            status = GenerationTaskStatus(
                run_id=run_id,
                running=True,
                prompt=request.prompt,
                provider=request.provider,
                model=request.model,
                started_at=_now_iso(),
            )
            task = _Task(run_id=run_id, proc=proc, log_path=log_path, status=status)
            self._tasks[run_id] = task
            asyncio.create_task(self._watch(task, log_file))
            return status

    async def _watch(self, task: _Task, log_file: IO[bytes]) -> None:
        try:
            returncode = await task.proc.wait()
        finally:
            log_file.close()
        task.status = task.status.model_copy(
            update={
                "running": False,
                "finished_at": _now_iso(),
                "returncode": returncode,
                "error": _tail_text(task.log_path) if returncode != 0 else None,
            }
        )
