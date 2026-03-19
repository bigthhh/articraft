from __future__ import annotations

from agent.harness import ArticraftAgent


def test_post_success_design_audit_injected_once() -> None:
    agent = ArticraftAgent.__new__(ArticraftAgent)
    agent._post_success_design_audit_sent = False
    agent.trace_writer = None

    conversation: list[dict] = []
    injected = agent._maybe_inject_post_success_design_audit(conversation)

    assert injected is True
    assert conversation
    content = conversation[0]["content"]
    assert "Compile passed. Do a final design audit before concluding." in content
    assert "hero features are prominent and unobscured" in content
    assert "dominant silhouette reads correctly" in content
    assert "prompt-specific claims" in content

    injected_again = agent._maybe_inject_post_success_design_audit(conversation)
    assert injected_again is False
    assert len(conversation) == 1
