from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

ToolSchema = dict[str, Any]
ConversationMessage = dict[str, Any]
ProviderResponse = dict[str, Any]


@dataclass(slots=True)
class ProviderTraceEvent:
    event_type: str
    payload: dict[str, Any]


@dataclass(slots=True)
class CompactionEvent:
    turn_before_request: int
    trigger: str
    model_id: str
    usage: dict[str, int] | None
    before_next_input_tokens: int | None
    after_next_input_tokens: int | None
    estimated_saved_next_input_tokens: int | None
    before_item_count: int
    after_item_count: int
    previous_response_id_cleared: bool
    guardrails: dict[str, Any] = field(default_factory=dict)
    estimate_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": "compaction",
            "turn_before_request": self.turn_before_request,
            "trigger": self.trigger,
            "model_id": self.model_id,
            "usage": dict(self.usage) if self.usage else None,
            "before_next_input_tokens": self.before_next_input_tokens,
            "after_next_input_tokens": self.after_next_input_tokens,
            "estimated_saved_next_input_tokens": self.estimated_saved_next_input_tokens,
            "before_item_count": self.before_item_count,
            "after_item_count": self.after_item_count,
            "previous_response_id_cleared": self.previous_response_id_cleared,
            "guardrails": dict(self.guardrails),
        }
        if self.estimate_error:
            payload["estimate_error"] = self.estimate_error
        return payload


@dataclass(slots=True)
class PrepareRequestResult:
    compaction_event: CompactionEvent | None = None
    maintenance_events: list[dict[str, Any]] = field(default_factory=list)
    trace_events: list[ProviderTraceEvent] = field(default_factory=list)


class ProviderClient(Protocol):
    """Common interface for model providers used by the runtime."""

    model_id: str

    def build_request_preview(
        self,
        *,
        system_prompt: str,
        messages: list[ConversationMessage],
        tools: list[ToolSchema],
    ) -> dict[str, Any]: ...

    async def prepare_next_request(
        self,
        *,
        system_prompt: str,
        messages: list[ConversationMessage],
        tools: list[ToolSchema],
        completed_turns: int,
        consecutive_compile_failure_count: int = 0,
        last_compile_failure_sig: str | None = None,
    ) -> Any: ...

    async def generate_with_tools(
        self,
        system_prompt: str,
        messages: list[ConversationMessage],
        tools: list[ToolSchema],
    ) -> ProviderResponse: ...

    async def close(self) -> Any: ...


@dataclass(slots=True, frozen=True)
class ProviderCapabilities:
    name: str
    supports_tools: bool = True
    supports_images: bool = False
    supports_reasoning_summary: bool = False
    supports_parallel_tool_calls: bool = False
