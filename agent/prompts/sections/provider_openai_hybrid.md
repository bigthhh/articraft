<tool_contract>
- Use ONLY `read_file`, `apply_patch`, `probe_model`, and `find_examples`.
- `read_file` is a JSON tool for reading the exact current text.
- `apply_patch` is a FREEFORM tool; send raw patch text only, not JSON.
- `probe_model` runs short Python snippets against the current bound model for inspection-only geometry diagnosis. The injected SDK docs contain the exact helper catalog and signatures.
- `find_examples` is lexical search over curated hybrid/CadQuery examples; use short concrete queries. Returned examples may include stale or deprecated SDK code, so treat them as inspiration/reference only and adapt against the current injected SDK docs instead of copying them verbatim.
- Do NOT provide `file_path`; the harness binds this run to one target file automatically.
- Use `probe_model` when placements, clearances, containment, or pose behavior are uncertain.
- Use `probe_model` only for non-mutating inspection. Do not write files, modify `object_model`, launch subprocesses, or perform network/destructive actions from it.
- Use `find_examples` before inventing an unfamiliar hybrid or CadQuery pattern.
- The target file already includes scaffolded editable code; modify that existing implementation rather than assuming a blank start.
- Stay in single-file mode: do not add, delete, or move files.
- Never paste Python code in chat; code changes must happen in tool calls. When finished, reply briefly and without code.
</tool_contract>
