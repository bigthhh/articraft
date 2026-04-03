from __future__ import annotations

from pathlib import Path

from agent.prompts import (
    DESIGNER_PROMPT_NAME,
    GEMINI_DESIGNER_PROMPT_NAME,
    HYBRID_GEMINI_DESIGNER_PROMPT_NAME,
    HYBRID_OPENAI_DESIGNER_PROMPT_NAME,
    OPENAI_DESIGNER_PROMPT_NAME,
    load_prompt_section_text,
    load_system_prompt_text,
    provider_system_prompt_suffix,
    resolve_system_prompt_path,
)


def test_system_prompt_resolution_variants() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    resolved = resolve_system_prompt_path(
        str(Path("agent/prompts/generated") / DESIGNER_PROMPT_NAME),
        provider="openai",
        repo_root=repo_root,
    )
    assert resolved.name == OPENAI_DESIGNER_PROMPT_NAME

    loaded_path, loaded_text = load_system_prompt_text(
        str(Path("agent/prompts/generated") / DESIGNER_PROMPT_NAME),
        provider="openai",
        repo_root=repo_root,
    )
    assert loaded_path == resolved
    assert loaded_text == resolved.read_text(encoding="utf-8")

    hybrid_resolved = resolve_system_prompt_path(
        str(Path("agent/prompts/generated") / DESIGNER_PROMPT_NAME),
        provider="openai",
        sdk_package="sdk_hybrid",
        repo_root=repo_root,
    )
    assert hybrid_resolved.name == HYBRID_OPENAI_DESIGNER_PROMPT_NAME

    gemini_resolved = resolve_system_prompt_path(
        str(Path("agent/prompts/generated") / DESIGNER_PROMPT_NAME),
        provider="gemini",
        repo_root=repo_root,
    )
    assert gemini_resolved.name == GEMINI_DESIGNER_PROMPT_NAME

    gemini_hybrid_resolved = resolve_system_prompt_path(
        str(Path("agent/prompts/generated") / DESIGNER_PROMPT_NAME),
        provider="gemini",
        sdk_package="sdk_hybrid",
        repo_root=repo_root,
    )
    assert gemini_hybrid_resolved.name == HYBRID_GEMINI_DESIGNER_PROMPT_NAME


def test_provider_system_prompt_suffixes() -> None:
    assert provider_system_prompt_suffix("openai") == ""
    assert provider_system_prompt_suffix("gemini") == ""


def test_compaction_prompt_section_loads_from_prompt_assets() -> None:
    prompt_path, prompt_text = load_prompt_section_text("gemini_compaction.md")

    assert prompt_path.name == "gemini_compaction.md"
    assert "Return JSON only." in prompt_text
