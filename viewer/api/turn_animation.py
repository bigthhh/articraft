from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TurnAnimationSpec:
    trace_line: int
    timestamp: float | None
    summary: str
    source: str


def _trace_tool_calls(row: dict[str, Any]) -> list[dict[str, Any]]:
    message = row.get("message")
    if not isinstance(message, dict):
        return []
    calls = message.get("tool_calls")
    return calls if isinstance(calls, list) else []


def _tool_call_name(call: dict[str, Any]) -> str | None:
    custom = call.get("custom")
    if isinstance(custom, dict) and isinstance(custom.get("name"), str):
        return str(custom["name"])
    function = call.get("function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return str(function["name"])
    return None


def _tool_call_patch_input(call: dict[str, Any]) -> str | None:
    custom = call.get("custom")
    if isinstance(custom, dict) and isinstance(custom.get("input"), str):
        return str(custom["input"])
    function = call.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("arguments"), str):
        return None
    try:
        arguments = json.loads(str(function["arguments"]))
    except json.JSONDecodeError:
        return None
    if isinstance(arguments, dict):
        value = arguments.get("patch") or arguments.get("input")
        if isinstance(value, str):
            return value
    return None


def _tool_call_args(call: dict[str, Any]) -> dict[str, Any]:
    custom = call.get("custom")
    if isinstance(custom, dict):
        return {"input": str(custom.get("input") or "")}
    function = call.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("arguments"), str):
        return {}
    try:
        args = json.loads(str(function["arguments"]))
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


def _tool_call_id(call: dict[str, Any]) -> str | None:
    value = call.get("id")
    return value if isinstance(value, str) and value else None


def _parse_tool_result(row: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    message = row.get("message")
    if not isinstance(message, dict) or message.get("role") != "tool":
        return None
    call_id = message.get("tool_call_id")
    name = message.get("name")
    content = message.get("content")
    if not isinstance(call_id, str) or not isinstance(name, str) or not isinstance(content, str):
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = {"result": content}
    if not isinstance(payload, dict):
        payload = {"result": payload}
    return call_id, name, payload


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(str(item["text"]))
        return "\n".join(parts)
    if content is None:
        return ""
    try:
        return json.dumps(content, ensure_ascii=False)
    except TypeError:
        return str(content)


def _collapse_text(value: str) -> str:
    return " ".join(value.split())


def _truncate_text(value: str, *, max_len: int = 420) -> str:
    collapsed = _collapse_text(value)
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 3].rstrip() + "..."


def _snippet_lines(value: str, *, max_lines: int = 20) -> list[str]:
    lines = value.splitlines()
    snippet = lines[:max_lines]
    if len(lines) > max_lines:
        snippet.append(f"... ({len(lines) - max_lines} more lines)")
    return snippet


def _indent_snippet(value: str, *, max_lines: int = 20) -> list[str]:
    return [
        f"    {line}" if line else "    " for line in _snippet_lines(value, max_lines=max_lines)
    ]


def _format_path_with_range(path: str, args: dict[str, Any]) -> str:
    offset = args.get("offset")
    limit = args.get("limit")
    if isinstance(offset, int) and isinstance(limit, int):
        return f"{path} L{offset}-L{offset + limit - 1}"
    if isinstance(offset, int):
        return f"{path} from L{offset}"
    return path


def _summarize_reads(calls: list[dict[str, Any]]) -> list[str]:
    reads: list[str] = []
    for call in calls:
        name = _tool_call_name(call)
        args = _tool_call_args(call)
        if name == "read_file":
            path = args.get("path")
            if isinstance(path, str) and path:
                reads.append(_format_path_with_range(path, args))
            else:
                reads.append("read_file")
        elif name == "read_code":
            reads.append("model.py editable section")
        elif name == "find_examples":
            query = args.get("query") or args.get("prompt") or args.get("description")
            reads.append(
                f"examples for {_truncate_text(str(query), max_len=80)}" if query else "examples"
            )
        elif name == "probe_model":
            reads.append("compiled model geometry probe")
    return reads


def _read_snippet_from_payload(payload: dict[str, Any]) -> str | None:
    result = payload.get("result")
    if isinstance(result, str) and result.strip():
        return result
    return None


def _summarize_read_snippets(
    calls: list[dict[str, Any]],
    results_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    snippets: list[str] = []
    for call in calls:
        name = _tool_call_name(call)
        call_id = _tool_call_id(call)
        payload = results_by_id.get(call_id or "")
        if payload is None or name not in {"read_file", "read_code", "find_examples"}:
            continue
        snippet = _read_snippet_from_payload(payload)
        if not snippet:
            continue
        args = _tool_call_args(call)
        title = name
        if name == "read_file":
            path = args.get("path")
            title = str(path) if isinstance(path, str) and path else "read_file"
        snippets.append(title)
        snippets.extend(_indent_snippet(snippet))
    return snippets


def _summarize_tool_calls(calls: list[dict[str, Any]]) -> list[str]:
    names = [_tool_call_name(call) for call in calls]
    clean_names = [name for name in names if name]
    if not clean_names:
        return []
    counts: dict[str, int] = {}
    for name in clean_names:
        counts[name] = counts.get(name, 0) + 1
    return [f"{name} x{count}" if count > 1 else name for name, count in counts.items()]


def _patch_hunk_count(patch: str) -> int:
    return sum(1 for line in patch.splitlines() if line.startswith("@@"))


def _summarize_writes(calls: list[dict[str, Any]]) -> list[str]:
    writes: list[str] = []
    for call in calls:
        name = _tool_call_name(call)
        args = _tool_call_args(call)
        if name == "apply_patch":
            patch = str(args.get("input") or "")
            if "model.py" not in patch:
                continue
            hunk_count = _patch_hunk_count(patch)
            suffix = "s" if hunk_count != 1 else ""
            writes.append(f"model.py via apply_patch ({hunk_count or 1} hunk{suffix})")
        elif name in {"edit_code", "replace"}:
            writes.append("model.py targeted replacement")
        elif name == "write_code":
            writes.append("model.py editable section rewrite")
        elif name == "write_file":
            path = args.get("path")
            writes.append(
                str(path) if isinstance(path, str) and path else "model.py editable section rewrite"
            )
    return writes


def _write_snippet(call: dict[str, Any]) -> tuple[str, str] | None:
    name = _tool_call_name(call)
    args = _tool_call_args(call)
    if name == "apply_patch":
        patch = str(args.get("input") or "")
        if "model.py" not in patch:
            return None
        return "apply_patch", patch
    if name == "edit_code":
        new_string = args.get("new_string")
        if isinstance(new_string, str) and new_string:
            return "edit_code new_string", new_string
    if name == "replace":
        new_string = args.get("new_string")
        if isinstance(new_string, str) and new_string:
            return "replace new_string", new_string
    if name == "write_code":
        code = args.get("code")
        if isinstance(code, str) and code:
            return "write_code code", code
    if name == "write_file":
        content = args.get("content")
        if isinstance(content, str) and content:
            return "write_file content", content
    return None


def _summarize_write_snippets(calls: list[dict[str, Any]]) -> list[str]:
    snippets: list[str] = []
    for call in calls:
        snippet = _write_snippet(call)
        if snippet is None:
            continue
        title, text = snippet
        snippets.append(title)
        snippets.extend(_indent_snippet(text))
    return snippets


def _tool_status(payload: dict[str, Any]) -> tuple[bool, str | None]:
    error = payload.get("error")
    if isinstance(error, str) and error.strip():
        return False, _truncate_text(error, max_len=180)
    compilation = payload.get("compilation")
    if isinstance(compilation, dict):
        status = compilation.get("status")
        comp_error = compilation.get("error")
        if status == "error":
            detail = comp_error if isinstance(comp_error, str) else "compilation error"
            return False, _truncate_text(detail, max_len=180)
        if status == "success":
            return True, None
    return True, None


def _compile_signal_summary(text: str) -> str | None:
    match = re.search(r"<summary>\s*(.*?)\s*</summary>", text, flags=re.DOTALL)
    if match:
        return _truncate_text(match.group(1), max_len=180)
    stripped = _collapse_text(text)
    return _truncate_text(stripped, max_len=180) if stripped else None


def _summarize_validations(calls: list[dict[str, Any]]) -> list[str]:
    validations: list[str] = []
    for call in calls:
        if _tool_call_name(call) == "compile_model":
            validations.append("compile_model: compile + QC/tests")
    return validations


def _summarize_results(
    calls: list[dict[str, Any]],
    results_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    results: list[str] = []
    for call in calls:
        name = _tool_call_name(call)
        call_id = _tool_call_id(call)
        payload = results_by_id.get(call_id or "")
        if name == "compile_model":
            if payload is None:
                results.append("pending: compile_model requested")
                continue
            ok, detail = _tool_status(payload)
            result = payload.get("result")
            if isinstance(result, str):
                detail = _compile_signal_summary(result) or detail
            results.append(
                f"{'passed' if ok else 'failed'}: compile_model"
                + (f" - {detail}" if detail else "")
            )
        elif (
            name in {"edit_code", "replace", "write_code", "write_file", "apply_patch"}
            and payload is not None
        ):
            compilation = payload.get("compilation")
            if isinstance(compilation, dict):
                ok, detail = _tool_status(payload)
                results.append(
                    f"{'passed' if ok else 'failed'}: syntax check after {name}"
                    + (f" - {detail}" if detail else "")
                )
    return results


def _summarize_tool_outcomes(
    calls: list[dict[str, Any]],
    results_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    outcomes: list[str] = []
    for call in calls:
        name = _tool_call_name(call)
        call_id = _tool_call_id(call)
        if not name or name == "compile_model":
            continue
        payload = results_by_id.get(call_id or "")
        if payload is None:
            continue
        ok, detail = _tool_status(payload)
        if ok and name in {"read_file", "read_code", "find_examples", "probe_model"}:
            continue
        outcomes.append(
            f"{'passed' if ok else 'failed'}: {name}" + (f" - {detail}" if detail else "")
        )
    return outcomes


def _append_section(lines: list[str], title: str, items: list[str]) -> None:
    if not items:
        return
    lines.append("")
    lines.append(f"{title}:")
    lines.extend(f"- {item}" for item in items)


def _assistant_summary(
    message: dict[str, Any],
    calls: list[dict[str, Any]],
    tool_result_rows: list[dict[str, Any]],
) -> str:
    thought_summary = message.get("thought_summary")
    content_summary = _message_text(message.get("content"))
    summary_source = thought_summary if isinstance(thought_summary, str) else content_summary
    summary = _truncate_text(summary_source) if summary_source.strip() else " "

    results_by_id: dict[str, dict[str, Any]] = {}
    for row in tool_result_rows:
        parsed = _parse_tool_result(row)
        if parsed is None:
            continue
        call_id, _, payload = parsed
        results_by_id[call_id] = payload

    lines = [summary]
    _append_section(lines, "Tool calls", _summarize_tool_calls(calls))
    _append_section(lines, "Reads", _summarize_reads(calls))
    _append_section(lines, "Read snippets", _summarize_read_snippets(calls, results_by_id))
    _append_section(lines, "Writes", _summarize_writes(calls))
    _append_section(lines, "Write snippets", _summarize_write_snippets(calls))
    _append_section(lines, "Validations", _summarize_validations(calls))
    _append_section(lines, "Results", _summarize_results(calls, results_by_id))
    _append_section(lines, "Tool outcomes", _summarize_tool_outcomes(calls, results_by_id))
    return "\n".join(lines)


def build_turn_animation_specs(
    rows: list[dict[str, Any]],
    initial_source: str,
    *,
    apply_patch_to_text: Callable[[str, str], str],
) -> tuple[list[TurnAnimationSpec], int]:
    current_source = initial_source
    specs: list[TurnAnimationSpec] = []
    skipped_count = 0
    assistant_rows: list[tuple[int, dict[str, Any], list[dict[str, Any]]]] = []

    for line_number, row in enumerate(rows, start=1):
        message = row.get("message")
        if isinstance(message, dict) and message.get("role") == "assistant":
            assistant_rows.append((line_number, row, []))
            continue
        if assistant_rows:
            parsed_tool_result = _parse_tool_result(row)
            if parsed_tool_result is not None:
                assistant_rows[-1][2].append(row)

    for line_number, row, tool_result_rows in assistant_rows:
        message = row.get("message")
        if not isinstance(message, dict):
            continue

        calls = _trace_tool_calls(row)
        for call in calls:
            if _tool_call_name(call) != "apply_patch":
                continue
            patch = _tool_call_patch_input(call)
            if not patch or "model.py" not in patch:
                continue
            try:
                current_source = apply_patch_to_text(current_source, patch)
            except ValueError:
                skipped_count += 1

        specs.append(
            TurnAnimationSpec(
                trace_line=line_number,
                timestamp=(row.get("ts") if isinstance(row.get("ts"), (int, float)) else None),
                summary=_assistant_summary(message, calls, tool_result_rows),
                source=current_source,
            )
        )

    return specs, skipped_count
