# Tool-only editing (mandatory)
- Use ONLY `read_file` and `apply_patch` to interact with the file.
- `read_file` is a normal tool with JSON args like `{"offset": 1, "limit": 200}`.
- `apply_patch` is a FREEFORM tool. Send raw patch text only, not JSON.
- Do NOT provide `file_path`; the harness binds this run to one target file automatically.
- Never paste Python code in chat; code changes must be in tool calls. When finished, reply with a brief message and no code.

# Editing strategy (important)
- Begin with `read_file` so you can see the exact current text and line numbers before patching.
- Keep edits surgical: patch the smallest stable region possible instead of rewriting the whole file.
- After ANY failed patch or syntax error, call `read_file` again and copy the exact current lines before retrying.
- If you need to replace a whole section, anchor on stable section headers/comments and patch only that section, not the entire file.
- Prefer one focused `apply_patch` with one or a few hunks over speculative rewrites.
- If the editable section starts empty, patch between the existing editable markers and insert `build_object_model()` plus `run_tests()`.
- Use this patch envelope:
  - `*** Begin Patch`
  - `*** Update File: CURRENT_FILE`
  - `@@`
  - hunk lines starting with space / `+` / `-`
  - `*** End Patch`
- Single-file mode only:
  - Do not use `*** Add File`, `*** Delete File`, or `*** Move to`.
- If two compile/test failures occur in a row, do a root-cause pass from the latest failure before patching again.
- After a compile, QC, or test failure, classify it as a local implementation bug, a wrong geometric representation, or a wrong overall composition.
- Fix failures at the right level. Keep edits surgical for local bugs, but rewrite the affected geometry/tests together when the representation or composition is wrong.
- If two repair turns in a row do not materially improve the named hero features, or keep the same failure class alive, stop patching locally and rewrite the affected region.
- Do not preserve a scaffold just because parts of it compile; preserve only the regions that still support a strong, prompt-faithful design.
