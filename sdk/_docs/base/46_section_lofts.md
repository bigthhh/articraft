# Section Lofts (`sdk.mesh`)

Use section lofts when you want to build a shell or exterior form from a small
number of authored cross-sections.

Import:

```python
from sdk import SectionLoftSpec, section_loft, repair_loft
```

```python
section_loft(spec, /, **overrides) -> MeshGeometry
repair_loft(geometry_or_spec, /, *, repair="auto") -> MeshGeometry
```

This is the recommended general loft API in the base `sdk`. It is not exposed
from `sdk_hybrid`.

## Intended usage

Use `section_loft(...)` when you can describe the shape with:

- 2 or more ordered section loops
- an optional centerline path
- an optional symmetry hint

This is a good fit for:

- outer shells
- tapered housings
- consumer-product casings
- simple bent lofts driven by a path

Prefer this over direct `LoftGeometry(...)` authoring for new lofted shapes.

## `section_loft(...)`

The simplest form is a list of section loops:

```python
geom = section_loft(
    [
        [(-0.05, -0.03, 0.00), (0.05, -0.03, 0.00), (0.05, 0.03, 0.00), (-0.05, 0.03, 0.00)],
        [(-0.03, -0.02, 0.08), (0.03, -0.02, 0.08), (0.03, 0.02, 0.08), (-0.03, 0.02, 0.08)],
    ]
)
```

You can also pass a `SectionLoftSpec` when you need named options:

```python
geom = section_loft(
    SectionLoftSpec(
        sections=(section0, section1, section2),
        path=((0.0, 0.0, 0.0), (0.02, 0.01, 0.04), (0.04, 0.0, 0.08)),
        symmetry="mirror_yz",
    )
)
```

### Parameters

`section_loft(...)` accepts either:

- `spec`: a `SectionLoftSpec`
- `spec`: a raw sequence of section loops

`SectionLoftSpec` fields:

- `sections`: required ordered cross-sections. Each section is a closed loop of
  3D points. At least two sections are required.
- `path`: optional 3D path used to drive a multisection sweep instead of a
  straight loft.
- `guide_curves`: optional advanced rails. In practice, the most useful key is
  `spine` as a path alias, plus `aux_spine` for extra orientation control.
- `cap`: request end caps.
- `solid`: request a solid result when the backend can produce one.
- `symmetry`: optional symmetry mode. The supported value is `mirror_yz`.
- `repair`: repair mode. Use `auto` unless you have a specific reason to turn
  repair off or force one stage.

Advanced backend controls also exist on `SectionLoftSpec`, but they are not the
normal authoring path and should usually be left at their defaults.

Advanced backend controls on `SectionLoftSpec`:

- `ruled`: request a ruled surface between sections instead of a smoother loft.
  This is mainly useful when you want flatter, more faceted transitions.
- `continuity`: backend continuity target for lofted surfaces. Supported values
  are `C1`, `C2`, and `C3`.
- `parametrization`: backend section matching strategy. Supported values are
  `uniform`, `chordal`, and `centripetal`.
- `degree`: requested surface degree. Higher values can allow smoother lofts,
  but they also make the result more backend-sensitive.
- `compat`: backend compatibility toggle for matching section topology during
  loft construction.
- `smoothing`: request additional backend smoothing during loft construction.
- `weights`: backend weight tuple used with smoothing behavior.
- `tessellation`: `LoftTessellation(...)` settings used when converting the
  backend result back into `MeshGeometry`.

`LoftTessellation` fields:

- `tolerance`: linear tessellation tolerance. Smaller values usually create a
  denser mesh.
- `angular_tolerance`: angular tessellation tolerance. Smaller values usually
  preserve curved regions more closely.

These controls are primarily for tuning or debugging difficult lofts. They are
not a good default authoring surface for LLM-generated geometry.

### Input expectations

For reliable results:

- keep section order consistent from start to end
- keep each section as one simple loop
- use roughly corresponding points around each loop when possible
- use a small number of plausible sections rather than many noisy ones

The implementation normalizes obvious issues such as repeated closing points and
simple winding inconsistencies, but it is still better to author clean loops.

### Path behavior

If `path` is omitted, `section_loft(...)` builds a regular loft through the
provided section loops.

If `path` is provided, `section_loft(...)` switches to a path-driven
multisection sweep. This is useful when the overall form bends or follows a
centerline.

## `repair_loft(...)`

Use `repair_loft(...)` in two cases:

- you already have a `MeshGeometry` loft that needs cleanup
- you want to regenerate a loft spec with a specific repair mode

Examples:

```python
clean = repair_loft(dirty_mesh)
```

```python
clean = repair_loft(spec, repair="mesh")
```

### Parameters

- `geometry_or_spec`: either a `MeshGeometry`, a `SectionLoftSpec`, or raw
  section loops
- `repair`: one of `auto`, `mesh`, `kernel`, or `off`

### Repair modes

- `auto`: run the default repair path
- `mesh`: run mesh-side cleanup
- `kernel`: prefer kernel-side healing before tessellation
- `off`: skip repair

When the input is already a `MeshGeometry`, `repair_loft(...)` performs mesh
repair only. When the input is a loft spec, it rebuilds the loft using the
requested repair mode.

## Practical guidance

- Start with raw sections and `section_loft(...)`.
- Add `path` only when the shape needs to bend.
- Use `symmetry="mirror_yz"` when you only want to author one side.
- Use `repair_loft(...)` when sparse or rough inputs produce a messy mesh.
- Keep `LoftGeometry(...)` for low-level or legacy cases, not new authoring.
