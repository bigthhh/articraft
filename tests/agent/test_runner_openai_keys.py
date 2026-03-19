from __future__ import annotations

from agent import runner


def test_runner_accepts_openai_api_keys_env(monkeypatch) -> None:
    async def fake_run_from_input(*args: object, **kwargs: object) -> int:
        return 0

    monkeypatch.setenv("OPENAI_API_KEYS", "key-a,key-b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(runner, "run_from_input", fake_run_from_input)

    exit_code = runner.main(["--prompt", "test prompt", "--provider", "openai"])

    assert exit_code == 0
