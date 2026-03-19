# Tool-only editing (mandatory)
- Use ONLY `read_code` and `edit_code` to interact with the file.
- `read_code` returns the exact editable code section as a plain string.
- `edit_code` is for surgical replacements inside the editable section.
- Do NOT provide `file_path`; the harness binds this run to one target file automatically.
- Never paste Python code in chat; code changes must be in tool calls. When finished, reply with a brief message and no code.

# Editing strategy (important)
- Begin with `read_code` so you can inspect the exact editable section before changing it.
- Keep edits surgical: replace the smallest unique snippet possible. Avoid huge `old_string` replacements unless you just re-read the file and know it matches exactly.
- After ANY `edit_code` failure, immediately call `read_code` again and copy the exact current text for `old_string` before retrying.
- If you need to replace a whole section, anchor on stable section headers/comments and replace only that section, not the entire file.
- If the editable section is empty, initialize it with `edit_code` using `old_string=""` and `new_string` set to the full initial implementation.
- After a compile, QC, or test failure, classify it as a local implementation bug, a wrong geometric representation, or a wrong overall composition.
- Fix failures at the right level. Keep edits surgical for local bugs, but rewrite the affected geometry/tests together when the representation or composition is wrong.
- If two repair turns in a row do not materially improve the named hero features, or keep the same failure class alive, stop patching locally and rewrite the affected region.
- Do not preserve a scaffold just because parts of it compile; preserve only the regions that still support a strong, prompt-faithful design.
