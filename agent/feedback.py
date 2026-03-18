from __future__ import annotations

import linecache
import re
import traceback

CODE_PATTERN = re.compile(
    r"```(?:python)?\s*\n"
    r"|^(?:from\s+\w+\s+import\s|import\s+\w+|def\s+\w+\s*\(|class\s+\w+)",
    re.MULTILINE,
)
LOFT_PROFILE_AREA_ERROR = "Loft profile area must be non-zero"
LOFT_PROFILE_AREA_HINT = (
    "Hint: LoftGeometry checks profile area in the XY projection. "
    "Use closed loops like `(x_i, y_i, z_const)`. "
    "If you need an XZ/YZ section, author it in XY first and rotate the mesh afterward."
)


def contains_code_in_text(text: str) -> bool:
    """Check if a model text response pasted code instead of using tools."""
    if not text:
        return False
    return bool(CODE_PATTERN.search(text))


def _compile_hint_lines(detail_lines: list[str]) -> list[str]:
    if any(LOFT_PROFILE_AREA_ERROR in line for line in detail_lines):
        return [LOFT_PROFILE_AREA_HINT]
    return []


def format_compile_exception(exc: BaseException, *, max_detail_lines: int = 40) -> str:
    """Compact compile exceptions for agent feedback without duplicated trace blocks."""
    raw_message = str(exc).strip()
    if raw_message:
        tb_marker = "Traceback (most recent call last):"
        marker_idx = raw_message.find(tb_marker)
        if marker_idx >= 0:
            raw_message = raw_message[:marker_idx].rstrip()

    detail_lines: list[str] = []
    seen: set[str] = set()
    for line in raw_message.splitlines():
        cleaned = line.rstrip()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        detail_lines.append(cleaned)

    warnings = getattr(exc, "warnings", None)
    if isinstance(warnings, list):
        for warning in warnings:
            cleaned = str(warning).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            detail_lines.append(cleaned)

    if len(detail_lines) > max_detail_lines:
        omitted = len(detail_lines) - max_detail_lines
        detail_lines = detail_lines[:max_detail_lines]
        detail_lines.append(f"... ({omitted} more lines)")

    for hint in _compile_hint_lines(detail_lines):
        if hint not in seen:
            detail_lines.append(hint)
            seen.add(hint)

    extracted = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
    location = ""
    code_line = ""
    skip_wrapper_location = isinstance(exc, RuntimeError)
    if extracted and not skip_wrapper_location:
        last = extracted[-1]
        location = f"{last.filename}:{last.lineno}"
        raw_line = linecache.getline(last.filename, last.lineno).rstrip("\n")
        if raw_line.strip():
            code_line = raw_line

    parts = [f"URDF compile failed: {type(exc).__name__}"]
    parts.extend(detail_lines)
    if location:
        parts.append(f"Location: {location}")
    if code_line:
        parts.append(f"Code: {code_line}")
    return "\n".join(parts)
