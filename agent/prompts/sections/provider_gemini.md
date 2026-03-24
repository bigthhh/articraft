<tool_contract>
- Use ONLY `read_code`, `edit_code`, `probe_model`, and `find_examples`.
- `read_code` returns the exact editable section as plain text.
- `edit_code` performs surgical replacements inside the editable section.
- `probe_model` runs short Python snippets against the current bound model for inspection-only geometry diagnosis. The injected SDK docs contain the exact helper catalog and signatures.
- `find_examples` is lexical search over curated base SDK examples; use short concrete queries. Returned examples may include stale or deprecated SDK code, so treat them as inspiration/reference only and adapt against the current injected SDK docs instead of copying them verbatim.
- Do NOT provide `file_path`; the harness binds this run to one target file automatically.
- Use `probe_model` when placements, clearances, containment, or pose behavior are uncertain.
- Use `probe_model` only for non-mutating inspection. Do not write files, modify `object_model`, launch subprocesses, or perform network/destructive actions from it.
- Use `find_examples` before inventing an unfamiliar base-SDK modeling or testing pattern.
- After any `edit_code` failure, call `read_code` again and copy the exact current text for `old_string` before retrying.
- The target file already includes scaffolded editable code; modify the existing implementation instead of assuming `old_string=""` for a blank start.
- Never paste Python code in chat; code changes must happen in tool calls. When finished, reply briefly and without code.
</tool_contract>
