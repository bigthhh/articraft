<process>
- Work evidence-first. Before editing, read `model.py`, read the specific SDK docs needed for the object/mechanism, and use `find_examples` for one or two relevant construction patterns.
- Do not keep planning in assistant text. Once you know the next concrete step, use a tool.
- Build from grounded evidence:
  1. Inspect the current code and relevant docs/examples.
  2. Identify the root body, articulated parts, joint origins, joint axes, motion limits, visible realism features, and exact tests.
  3. Make one coherent implementation pass that creates a connected, mechanically credible baseline.
  4. Run `compile_model`.
  5. Repair compile/QC failures directly; use `probe_model` only when spatial evidence is needed.
- Treat overlap failures by classifying them first. Some overlaps are visually and mechanically valid, such as seated parts, hinge barrels, nested hardware, captured pins, and small hidden inserts. When an overlap is intentional and local, silence it with a scoped `ctx.allow_overlap(...)` plus an exact proof check instead of distorting the visible geometry to remove it.
- The first working version must establish a credible baseline: the primary mechanism, physical support, plausible proportions, and clear requested identity. Treat it as a baseline to build on, not the finish line.
- After every code mutation, compile before concluding.
- After a clean compile, complete every missing prompt-critical feature — secondary mechanisms, distinct visible controls, hollow/cut/curved surfaces still standing in as primitives, materials and colors — one focused edit and compile at a time, until no specific real feature is missing.
- Conclude only after the latest revision compiles cleanly and you cannot name a specific remaining defect.
</process>
