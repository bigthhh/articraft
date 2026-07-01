<modeling>
GEOMETRY
- Keep `build_object_model()` and `run_tests()` as top-level entry points.
- Import public authoring APIs directly from `sdk`.
- Do not guess Python submodules from docs topic names. For example, use `from sdk import place_on_face`, not `from sdk.placement import place_on_face`.
- Use primitives only when they represent the visible form credibly. Do not use capped primitive solids as substitutes for visible hollow bodies, cut openings, inset cavities, curved shells, rings, grilles, or layered manufactured panels.
- Prefer CadQuery for visible geometry that needs lower-level shape control: hollow shells, open-ended cylinders/tubes, cut-through openings, boolean-cut panels, continuous curved forms, lofts, sweeps, recesses, lips, rims, and realistic appliance or machine housings.
- Mix primitives and CadQuery freely. A good model often uses primitives for hidden/simple structure and CadQuery for the visible parts where primitives would read as placeholders.
- CadQuery quick reference for visible detail (wrap each result with `mesh_from_cadquery(solid, "logical_name")`): hollow shells via `.faces(">Z").shell(-wall)`; through-holes and cutouts via `.faces(">Z").workplane().hole(d)` or a boolean cut; rounded or relieved edges via `.edges("|Z").fillet(r)` or `.chamfer(c)`; smooth or tapered transitions via lofts and sweeps along a wire. Reach for these whenever a primitive would only stand in for a hollow, cut, curved, or relieved surface.
- Generate repeated features parametrically instead of hand-placing a few. For teeth, perforations, fins, spokes, slats, louvers, or chain links, write a small helper plus a Python loop driven by real counts and spacing so the density reads like the real object.
- Match the visible construction logic of the object. If a face should read as one continuous manufactured piece, keep it as a connected face with openings or cutouts instead of rebuilding it from separate floating members. Use separate member-based construction only when the visible form should genuinely read as discrete members.
- When authoring mesh-backed visuals, use managed logical names like `mesh_from_geometry(..., "door_panel")` or `mesh_from_cadquery(..., "door_panel")`; do not reason about filesystem paths.
- Author visual geometry only; do not author collision geometry in `sdk`.
- Preserve correct joint origins, axes, limits, and articulation behavior.

TESTING
- Use `sdk.TestContext`, return `ctx.report()`, and let `compile_model` own the baseline sanity/QC pass.
- Prefer `TestContext(object_model)`; do not pass asset roots in new code.
- Use `run_tests()` for prompt-specific exact checks, targeted pose checks, and explicit allowances only.
- Treat overlap findings as classification tasks first: decide whether the reported intersection is intentional design embedding that should be covered by a scoped `ctx.allow_overlap(...)`, or an unintended collision that needs geometry, mount, or pose changes. Accepted intentional cases include proxy nesting, captured pins or shafts, seated trim, and compliant compression.
- Pair every `ctx.allow_overlap(...)` with at least one exact proof check such as `expect_within(...)`, `expect_overlap(...)`, `expect_gap(..., max_penetration=...)`, `expect_contact(...)`, or a decisive pose check.
</modeling>
