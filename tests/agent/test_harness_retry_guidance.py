from __future__ import annotations

from agent.harness import ArticraftAgent


def test_compile_retry_message_classifies_failure_level() -> None:
    agent = ArticraftAgent.__new__(ArticraftAgent)
    agent._last_compile_error_sig = None
    agent.trace_writer = None

    conversation: list[dict] = []
    content = agent._append_compile_retry_message(
        conversation,
        formatted="URDF compile failed.\nValueError: bad loft",
    )

    assert "diagnostic signal" in content
    assert "local bug" in content
    assert "wrong geometric representation" in content
    assert "wrong overall composition" in content
    assert conversation


def test_repeated_compile_retry_message_escalates_to_rewrite() -> None:
    agent = ArticraftAgent.__new__(ArticraftAgent)
    agent._last_compile_error_sig = None
    agent.trace_writer = None

    formatted = "URDF compile failed.\nValueError: bad loft"
    conversation: list[dict] = []
    agent._append_compile_retry_message(conversation, formatted=formatted)
    content = agent._append_compile_retry_message(conversation, formatted=formatted)

    assert "Same compile failure as previous turn" in content
    assert "repeated diagnostic signal" in content
    assert "rewrite the affected region from the root cause" in content
    assert "visually wrong scaffold" in content
