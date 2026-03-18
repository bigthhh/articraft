from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


from agent.prompts.compile import compile_prompt_variant
from agent.prompts.spec import iter_prompt_variants

OLD_OPENAI_PROMPT = Path(
    "/Users/matthewzhou/particulate-v2/synth-urdf-agent/designer_system_prompt_openai.txt"
)


def main() -> None:
    assert OLD_OPENAI_PROMPT.exists(), f"Missing old prompt baseline: {OLD_OPENAI_PROMPT}"
    expected = OLD_OPENAI_PROMPT.read_text(encoding="utf-8")

    variant = next(
        variant
        for variant in iter_prompt_variants()
        if variant.output.name == "designer_system_prompt_openai.txt"
    )
    compiled = compile_prompt_variant(variant)
    generated = variant.output.read_text(encoding="utf-8")

    assert compiled == expected, "Compiled OpenAI designer prompt no longer matches old baseline"
    assert generated == expected, "Generated OpenAI designer prompt no longer matches old baseline"


if __name__ == "__main__":
    main()
