You are compacting Articraft Gemini run history into a single handoff summary.

Goal:
- Preserve the information needed for the next coding/debugging turn.
- Compress older history without dropping task-defining constraints or active failure context.

Required preserved facts:
- The object/task request and success-defining requirements.
- Important dimensions, geometry constraints, and acceptance-critical details.
- Important example/tool findings already discovered.
- Current compile/debug state, especially unresolved failures and warnings.
- Concrete next-step context that would matter on the very next turn.

Forbidden omissions:
- Do not omit required dimensions or spatial relationships.
- Do not omit compile failures that are still unresolved.
- Do not omit user-provided constraints, exclusions, or design preferences.
- Do not omit important example references if they still guide the implementation.

Output format:
- Return JSON only.
- Use this exact schema:
  - `task_requirements`: array of strings
  - `constraints`: array of strings
  - `tool_findings`: array of strings
  - `compile_state`: array of strings
  - `next_steps`: array of strings
- Keep each entry concise and specific.
- Prefer preserving concrete facts over prose.
- Do not include markdown fences.
