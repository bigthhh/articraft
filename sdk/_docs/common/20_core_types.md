# Core Types

Import these from top-level `sdk`:

```python
from sdk import (
    Origin,
    Box,
    Cylinder,
    Sphere,
    Mesh,
    Material,
    Visual,
    Inertia,
    Inertial,
    MotionLimits,
    MotionProperties,
    Part,
    Articulation,
    ArticulationType,
)
```

## Coordinates

- Distances are meters.
- Rotations are roll/pitch/yaw in radians.
- URDF cylinders are aligned with local `+Z`.

## Geometry

- `Box(size=(sx, sy, sz))`
- `Cylinder(radius=r, length=l)`
- `Sphere(radius=r)`
- `Mesh(filename="assets/meshes/part.obj", scale=(sx, sy, sz) | None)`

Primitive geometry constructors describe shape only. Put transforms on the containing element.

### `scale_geometry_to_size(...)`

Use `scale_geometry_to_size(...)` when you know the final local extents you want
and do not want to manually derive scale factors.

```python
from sdk import AssetContext, Box, Mesh, scale_geometry_to_size

ASSETS = AssetContext.from_script(__file__)

shell = scale_geometry_to_size(
    Mesh(filename="assets/meshes/shell.obj"),
    (0.12, 0.08, 0.04),
    asset_root=ASSETS.asset_root,
)

panel = scale_geometry_to_size(
    Box((0.05, 0.10, 0.002)),
    (0.08, None, None),
)
```

Notes:

- `target_size` is `(x, y, z)` in meters, and each axis can be a positive
  float or `None`.
- `mode="stretch"` is the default. Use `mode="uniform"` to apply one shared
  scale factor instead.
- Resizing is anchored at the local origin. The helper does not add any origin
  compensation or recentering.
- If a `Cylinder` or `Sphere` resize would stop being representable as that
  primitive, pass `filename=...` so the helper can emit an OBJ-backed `Mesh`.

Primitive-to-mesh conversion example:

```python
from sdk import AssetContext, Sphere, scale_geometry_to_size

ASSETS = AssetContext.from_script(__file__)

badge = scale_geometry_to_size(
    Sphere(radius=0.02),
    (0.04, 0.06, 0.01),
    filename=ASSETS.mesh_path("badge.obj"),
)
```

## Material

Use the `Material` constructor directly when you want to create a material object yourself:

```python
steel = Material(name="steel", rgba=(0.55, 0.57, 0.60, 1.0))
glass = Material(name="glass", rgba=(0.72, 0.84, 0.92, 0.35))
```

Note:

- `Material(...)` uses `rgba=...`, not `color=...`.
- If you want the `color` alias, use `model.material(...)` on `ArticulatedObject` instead.

## Part

`Part` is the main authored geometry container.

Authoring is visual-first:

```python
part.visual(geometry, origin=Origin(...), material=..., name=...)
part.inertial = Inertial.from_geometry(geometry, mass=..., origin=Origin(...))
```

The `sdk` package no longer exposes collision-authoring helpers. Compile/export generates collisions automatically from visuals.

## Inertial

```python
Inertial.from_geometry(geometry, mass=..., origin=Origin(...) | None)
```

Supports `Box`, `Cylinder`, and `Sphere`.

## Articulation

```python
Articulation(
    name="hinge",
    articulation_type=ArticulationType.REVOLUTE,
    parent="base",
    child="lid",
    origin=Origin(...),
    axis=(0.0, 1.0, 0.0),
    motion_limits=MotionLimits(...) | None,
    motion_properties=MotionProperties(...) | None,
)
```

Use:

- `ArticulationType.REVOLUTE`
- `ArticulationType.CONTINUOUS`
- `ArticulationType.PRISMATIC`
- `ArticulationType.FIXED`
- `ArticulationType.FLOATING`

Strict motion-limit rules:

- `REVOLUTE` and `PRISMATIC` articulations must set `motion_limits=MotionLimits(...)` with positive `effort` and `velocity`, plus both `lower` and `upper`.
- `CONTINUOUS` articulations must set `motion_limits=MotionLimits(effort=..., velocity=...)`.
- `CONTINUOUS` articulations must not set `lower` or `upper`.
- `FIXED` and `FLOATING` articulations do not use `motion_limits`.

Example continuous articulation:

```python
Articulation(
    name="mast_slew",
    articulation_type=ArticulationType.CONTINUOUS,
    parent="chassis",
    child="mast",
    origin=Origin(...),
    axis=(0.0, 0.0, 1.0),
    motion_limits=MotionLimits(effort=12.0, velocity=1.5),
)
```

For authored models, the canonical constructor is `model.articulation(...)`.
