from __future__ import annotations

from agent.prompts.compile import compile_prompt_variant, find_stale_prompts
from agent.prompts.spec import iter_prompt_variants


def test_prompt_outputs_are_current() -> None:
    stale = find_stale_prompts()
    assert not stale, f"Generated prompts are stale: {[variant.output.name for variant in stale]}"

    compiled_by_name = {
        variant.output.name: compile_prompt_variant(variant) for variant in iter_prompt_variants()
    }

    assert "apply_patch" in compiled_by_name["designer_system_prompt_openai.txt"]
    assert "write_code" not in compiled_by_name["designer_system_prompt_openai.txt"]
    assert "wrong geometric representation" in compiled_by_name["designer_system_prompt_openai.txt"]
    assert "named hero features" in compiled_by_name["designer_system_prompt_openai.txt"]
    assert (
        "silhouette-critical visible forms" in compiled_by_name["designer_system_prompt_openai.txt"]
    )
    assert (
        "Plain primitives are acceptable for hidden structure"
        in compiled_by_name["designer_system_prompt_openai.txt"]
    )
    assert "sdk_hybrid" in compiled_by_name["designer_system_prompt_openai_hybrid.txt"]
    assert "edit_code" in compiled_by_name["designer_system_prompt_gemini.txt"]
    assert "read_code" in compiled_by_name["designer_system_prompt_gemini.txt"]
    assert "write_code" not in compiled_by_name["designer_system_prompt_gemini.txt"]
    assert "wrong geometric representation" in compiled_by_name["designer_system_prompt_gemini.txt"]
    assert "named hero features" in compiled_by_name["designer_system_prompt_gemini.txt"]
    assert (
        "silhouette-critical visible forms" in compiled_by_name["designer_system_prompt_gemini.txt"]
    )
    assert (
        "Plain primitives are acceptable for hidden structure"
        in compiled_by_name["designer_system_prompt_gemini.txt"]
    )
    assert "sdk_hybrid" in compiled_by_name["designer_system_prompt_gemini_hybrid.txt"]
