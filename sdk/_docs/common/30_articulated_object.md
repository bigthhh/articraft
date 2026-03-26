# ArticulatedObject

## Purpose

`ArticulatedObject` is the root authored assembly. Use it to create parts,
articulations, materials, and model-level metadata.

## Import

```python
from sdk import ArticulatedObject
```

## Recommended Surface

- `ArticulatedObject(...)`
- `model.part(...)`
- `model.articulation(...)`
- `model.material(...)`
- `model.get_part(...)`
- `model.get_articulation(...)`
- `model.root_parts()`
- `model.validate(strict=True)`

## Construction

```python
ArticulatedObject(
    name: str,
    parts: list[Part] = [],
    articulations: list[Articulation] = [],
    materials: list[Material] = [],
    meta: dict[str, object] = {},
    assets: AssetContext | None = None,
)
```

Important fields:

- `name`: model name.
- `parts`: authored parts.
- `articulations`: authored articulations.
- `materials`: registered materials.
- `meta`: optional model-level metadata.
- `assets`: optional asset context for mesh-backed models.

## Authoring Helpers

### `model.part(...)`

```python
model.part(
    name: str,
    *,
    visuals: Iterable[Visual] | None = None,
    inertial: Inertial | None = None,
    meta: dict[str, object] | None = None,
) -> Part
```

- Creates a `Part`, appends it to `model.parts`, and returns it.
- The returned part is the normal place to call `part.visual(...)`.

### `model.articulation(...)`

```python
model.articulation(
    name: str,
    articulation_type: ArticulationType | str,
    parent: str | Part,
    child: str | Part,
    *,
    origin: Origin | None = None,
    axis: tuple[float, float, float] | None = None,
    motion_limits: MotionLimits | None = None,
    motion_properties: MotionProperties | None = None,
    meta: dict[str, object] | None = None,
) -> Articulation
```

- `parent`, `child`: either part objects or part names.
- `origin`: articulation origin. Defaults to `Origin()`.
- `axis`: defaults to `(0.0, 0.0, 1.0)`.
- `motion_limits`: joint limits where required.
- `motion_properties`: optional damping and friction.

### `model.material(...)`

```python
model.material(
    name: str,
    *,
    rgba: Sequence[float] | None = None,
    color: Sequence[float] | None = None,
    texture: str | None = None,
) -> Material
```

- Registers the material on `model.materials`.
- Use either `rgba=...` or `color=...`, not both.
- A 3-tuple color is expanded to `(r, g, b, 1.0)`.

## Lookup Helpers

### `model.get_part(name) -> Part`

```python
model.get_part(name: str | Part) -> Part
```

Returns the named part. Raises `ValidationError` if it does not exist.

### `model.get_articulation(name) -> Articulation`

```python
model.get_articulation(name: str | Articulation) -> Articulation
```

Returns the named articulation. Raises `ValidationError` if it does not exist.

### `model.root_parts() -> list[Part]`

Returns all parts that are not the child of another articulation.

## Validation

### `model.validate(...)`

```python
model.validate(
    *,
    strict: bool = True,
    strict_mesh_paths: bool = False,
) -> None
```

Validation includes:

- at least one part exists
- part names are unique
- articulation names are unique
- material names are unique
- articulations reference existing parent and child parts
- each part has at most one parent articulation
- geometry and materials are valid
- in strict mode, the articulation graph is connected from at least one root

## Joint Rules

Use these rules when calling `model.articulation(...)`:

- `ArticulationType.REVOLUTE` and `ArticulationType.PRISMATIC` require
  `MotionLimits(effort=..., velocity=..., lower=..., upper=...)`.
- `ArticulationType.CONTINUOUS` requires
  `MotionLimits(effort=..., velocity=...)` and must not set `lower` or `upper`.
- `ArticulationType.FIXED` and `ArticulationType.FLOATING` must not use
  `motion_limits`.
- In strict mode, articulated motion axes must be non-zero 3-vectors.

## Example

```python
model = ArticulatedObject(name="desk_lamp")

base = model.part("base")
arm = model.part("arm")

model.articulation(
    "base_to_arm",
    ArticulationType.REVOLUTE,
    parent=base,
    child=arm,
    origin=Origin(xyz=(0.0, 0.0, 0.08)),
    axis=(0.0, 1.0, 0.0),
    motion_limits=MotionLimits(effort=5.0, velocity=2.0, lower=-0.8, upper=0.8),
)
```

## See Also

- `20_core_types.md` for `Part`, `Articulation`, `MotionLimits`, and materials
- `80_testing.md` for geometry and articulation QC
