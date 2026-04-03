from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from agent.providers.gemini import GeminiLLM, _gemini_compaction_prompt_text


def test_prepare_next_request_creates_prefix_cache_event() -> None:
    provider = GeminiLLM(dry_run=True)

    async def fake_count_prefix_tokens(
        *, system_prompt: str, tools: list[dict], messages: list[dict]
    ) -> int:
        assert system_prompt == "system"
        assert len(messages) == 2
        return 5000

    async def fake_create_prefix_cache(
        *, system_prompt: str, tools: list[dict], messages: list[dict]
    ) -> dict:
        return {
            "name": "cachedContents/cache_1",
            "expire_time": "2026-04-02T12:00:00Z",
            "usage_metadata": {"total_token_count": 5000, "cached_content_token_count": 5000},
        }

    provider._count_prefix_tokens = fake_count_prefix_tokens  # type: ignore[method-assign]
    provider._create_prefix_cache = fake_create_prefix_cache  # type: ignore[method-assign]

    result = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=[
                {"role": "user", "content": "sdk docs"},
                {"role": "user", "content": "task"},
            ],
            tools=[],
            completed_turns=0,
        )
    )

    assert result.compaction_event is None
    assert result.maintenance_events[0]["kind"] == "cache_create"
    assert result.maintenance_events[0]["cache_name"] == "cachedContents/cache_1"
    assert provider._cached_content_name == "cachedContents/cache_1"


def test_prepare_next_request_compacts_for_hard_pressure_and_preserves_raw_tail() -> None:
    provider = GeminiLLM(dry_run=True)
    provider._last_usage = {"prompt_tokens": 700_000}
    provider._cached_content_name = "cachedContents/cache_1"
    provider._cached_content_expire_time = datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc)

    async def fake_ensure_prefix_cache(
        *, system_prompt: str, tools: list[dict], trace_events: list
    ) -> list[dict]:
        return []

    counted_messages: list[list[str]] = []
    token_counts = iter([750_000, 150_000])

    async def fake_count_request_tokens(
        *, system_prompt: str, tools: list[dict], messages: list[dict]
    ) -> int:
        counted_messages.append([str(message.get("content")) for message in messages])
        return next(token_counts)

    async def fake_compact_messages(
        *, system_prompt: str, messages: list[dict]
    ) -> tuple[dict, dict[str, int]]:
        assert [message.get("content") for message in messages] == [
            "old assistant",
            "old tool result",
        ]
        return (
            {"role": "user", "content": "[System-generated compaction summary]\nsummary"},
            {"prompt_tokens": 10_000, "candidates_tokens": 500, "total_tokens": 10_500},
        )

    provider._ensure_prefix_cache = fake_ensure_prefix_cache  # type: ignore[method-assign]
    provider._count_request_tokens = fake_count_request_tokens  # type: ignore[method-assign]
    provider._compact_messages = fake_compact_messages  # type: ignore[method-assign]

    messages = [
        {"role": "user", "content": "sdk docs"},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "old assistant"},
        {
            "role": "tool",
            "name": "compile_model",
            "tool_call_id": "call_old",
            "content": "old tool result",
        },
        {"role": "assistant", "content": "latest assistant"},
        {
            "role": "tool",
            "name": "compile_model",
            "tool_call_id": "call_latest",
            "content": "latest tool result",
        },
        {"role": "user", "content": "fix latest"},
    ]

    result = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=messages,
            tools=[],
            completed_turns=2,
        )
    )

    assert result.compaction_event is not None
    assert result.compaction_event.trigger == "hard_pressure"
    assert result.compaction_event.before_next_input_tokens == 750_000
    assert result.compaction_event.after_next_input_tokens == 150_000
    assert result.compaction_event.estimated_saved_next_input_tokens == 600_000
    assert counted_messages == [
        ["latest assistant", "latest tool result", "fix latest"],
        [
            "[System-generated compaction summary]\nsummary",
            "latest assistant",
            "latest tool result",
            "fix latest",
        ],
    ]

    request_messages = provider._request_messages()
    assert request_messages[0]["content"].startswith("[System-generated compaction summary]")
    assert [message.get("content") for message in request_messages[1:]] == [
        "latest assistant",
        "latest tool result",
        "fix latest",
    ]


def test_prepare_next_request_soft_compaction_resets_after_compile_streak_reset() -> None:
    provider = GeminiLLM(dry_run=True)

    async def fake_ensure_prefix_cache(
        *, system_prompt: str, tools: list[dict], trace_events: list
    ) -> list[dict]:
        return []

    async def fake_count_request_tokens(
        *, system_prompt: str, tools: list[dict], messages: list[dict]
    ) -> int:
        return 100_000

    async def fake_compact_messages(
        *, system_prompt: str, messages: list[dict]
    ) -> tuple[dict, dict[str, int]]:
        return (
            {"role": "user", "content": "[System-generated compaction summary]\nsummary"},
            {"prompt_tokens": 1_000, "candidates_tokens": 50, "total_tokens": 1_050},
        )

    provider._ensure_prefix_cache = fake_ensure_prefix_cache  # type: ignore[method-assign]
    provider._count_request_tokens = fake_count_request_tokens  # type: ignore[method-assign]
    provider._compact_messages = fake_compact_messages  # type: ignore[method-assign]

    messages = [
        {"role": "user", "content": "sdk docs"},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "older assistant"},
        {
            "role": "tool",
            "name": "compile_model",
            "tool_call_id": "call_older",
            "content": "older tool result",
        },
        {"role": "assistant", "content": "latest assistant"},
        {
            "role": "tool",
            "name": "compile_model",
            "tool_call_id": "call_latest",
            "content": "latest tool result",
        },
    ]

    first = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=messages,
            tools=[],
            completed_turns=2,
            consecutive_compile_failure_count=3,
            last_compile_failure_sig="compile_sig",
        )
    )
    second = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=messages,
            tools=[],
            completed_turns=4,
            consecutive_compile_failure_count=3,
            last_compile_failure_sig="compile_sig",
        )
    )
    reset = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=messages,
            tools=[],
            completed_turns=5,
            consecutive_compile_failure_count=0,
            last_compile_failure_sig=None,
        )
    )
    third = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=messages,
            tools=[],
            completed_turns=6,
            consecutive_compile_failure_count=3,
            last_compile_failure_sig="compile_sig",
        )
    )

    assert first.compaction_event is not None
    assert second.compaction_event is None
    assert reset.compaction_event is None
    assert third.compaction_event is not None


def test_prepare_next_request_emits_skip_for_unsupported_threshold_model() -> None:
    provider = GeminiLLM(model_id="gemini-1.5-pro", dry_run=True)
    provider._last_usage = {"prompt_tokens": 800_000}

    async def fake_ensure_prefix_cache(
        *, system_prompt: str, tools: list[dict], trace_events: list
    ) -> list[dict]:
        return []

    provider._ensure_prefix_cache = fake_ensure_prefix_cache  # type: ignore[method-assign]

    result = asyncio.run(
        provider.prepare_next_request(
            system_prompt="system",
            messages=[
                {"role": "user", "content": "sdk docs"},
                {"role": "user", "content": "task"},
            ],
            tools=[],
            completed_turns=2,
        )
    )

    assert result.compaction_event is None
    assert [event.event_type for event in result.trace_events] == ["compaction_skipped"]


def test_gemini_compaction_prompt_is_loaded_from_prompt_asset() -> None:
    prompt_text = _gemini_compaction_prompt_text()
    assert "Return JSON only." in prompt_text


def test_close_emits_cache_delete_event() -> None:
    provider = GeminiLLM(dry_run=True)
    provider._cached_content_name = "cachedContents/cache_1"

    async def fake_delete_prefix_cache(cache_name: str) -> None:
        assert cache_name == "cachedContents/cache_1"

    provider._delete_prefix_cache = fake_delete_prefix_cache  # type: ignore[method-assign]

    events = asyncio.run(provider.close())

    assert events == [
        {
            "kind": "cache_delete",
            "type": "cache_delete",
            "model_id": provider.model_id,
            "cache_name": "cachedContents/cache_1",
            "usage": None,
            "accounting_status": "not_billed_v1",
        }
    ]
