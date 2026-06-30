from __future__ import annotations

import pytest

from agent.run_context import _build_single_run_slug, _slugify
from storage.identifiers import validate_record_id

NON_ASCII_PROMPTS = [
    "制作一扇门 木质风格",
    "日本語テスト",
    "café résumé",
    "Кириллица",
    "门 lamp 123",
]


@pytest.mark.parametrize("prompt", NON_ASCII_PROMPTS)
def test_slugify_is_ascii_only(prompt: str) -> None:
    slug = _slugify(prompt)
    assert slug
    assert slug.isascii()
    # A record id built from the slug must satisfy the ASCII-only RECORD_ID_RE.
    validate_record_id(f"rec_{slug}_20260101_000000_000000_abc123")


def test_slugify_preserves_ascii_tokens() -> None:
    assert _slugify("门 lamp 123") == "lamp-123"
    assert _slugify("an articulated desk lamp") == "an-articulated-desk-lamp"


def test_slugify_falls_back_to_object_for_pure_non_ascii() -> None:
    assert _slugify("制作一扇门 木质风格") == "object"
    assert _slugify("") == "object"


@pytest.mark.parametrize("prompt", NON_ASCII_PROMPTS)
def test_build_single_run_slug_stays_valid(prompt: str) -> None:
    slug = _build_single_run_slug(prompt * 20)
    assert slug.isascii()
    validate_record_id(f"rec_{slug}_20260101_000000_000000_abc123")
