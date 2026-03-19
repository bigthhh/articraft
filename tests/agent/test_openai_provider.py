from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import pytest

from agent.providers.openai import OpenAILLM, openai_api_keys_from_env


def test_openai_api_keys_from_env_supports_multiple_values() -> None:
    keys = openai_api_keys_from_env(
        {
            "OPENAI_API_KEYS": " key-a,\nkey-b,key-a ",
            "OPENAI_API_KEY": "key-c",
        }
    )

    assert keys == ["key-a", "key-b"]


def test_openai_api_keys_from_env_supports_single_key_fallback() -> None:
    keys = openai_api_keys_from_env({"OPENAI_API_KEY": "key-a"})

    assert keys == ["key-a"]


def test_openai_llm_builds_one_client_per_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_openai = types.ModuleType("openai")

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str):
            self.api_key = api_key
            self.base_url = "https://api.openai.com/v1/"
            self.responses = SimpleNamespace(create=self._create)

        async def _create(self, **_: object) -> dict[str, object]:
            return {"output": []}

        async def close(self) -> None:
            return None

    fake_openai.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("OPENAI_API_KEYS", "key-a,key-b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    llm = OpenAILLM()

    try:
        assert llm._api_keys == ["key-a", "key-b"]
        assert len(llm._clients) == 2
        assert llm._client.api_key == "key-a"
    finally:
        asyncio.run(llm.close())


def test_openai_llm_http_transport_tumbles_keys_between_attempts() -> None:
    llm = OpenAILLM(dry_run=True, transport="http")
    llm._clients = [object(), object()]
    llm._api_keys = ["key-a", "key-b"]
    llm._next_client_index = 1

    assert llm._select_request_client_index(last_attempt_client_index=None) == 1
    assert llm._select_request_client_index(last_attempt_client_index=1) == 0


def test_openai_llm_websocket_transport_sticks_to_one_key() -> None:
    llm = OpenAILLM(dry_run=True, transport="websocket")
    llm._clients = [object(), object()]
    llm._api_keys = ["key-a", "key-b"]
    llm._next_client_index = 1

    assert llm._select_request_client_index(last_attempt_client_index=None) == 1
    assert llm._select_request_client_index(last_attempt_client_index=1) == 1

    llm._previous_response_client_index = 1

    assert llm._select_request_client_index(last_attempt_client_index=None) == 1
    assert llm._select_request_client_index(last_attempt_client_index=1) == 1
