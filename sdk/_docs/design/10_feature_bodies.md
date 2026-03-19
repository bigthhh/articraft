# Feature Bodies (`sdk.body`) Design Draft

Status: proposal only. This file is a design note for a planned base-SDK
extension. It is not part of the current user-facing SDK docs profile, and the
APIs sketched here are not implemented yet.

## Problem

`section_loft(...)` is a good fit for one dominant shell or one continuous
limb. It is not a good public abstraction for:

- branching topology
- hard localized cuts, recesses, seams, bosses, and trims
- smooth handle/body or spout/body joins

OCCT can represent those forms, but the current SDK surface does not preserve
enough structured B-rep intent to make them easy or robust for an agent.

Today the public base-SDK authoring path is mostly:

- mesh primitives
- mesh booleans
- wire/tube sweeps
- one-stack section lofts

That is enough for mouse shells, simple casings, rails, and tubes. It is not
enough for mugs, kettles, watering cans, game controllers, or other objects
with multiple limbs and localized surface features.

## Goals

- Keep the easy path easy for shell-like consumer objects.
- Add a higher-level body-composition abstraction above raw OCCT/CadQuery.
- Avoid exposing kernel faces, edges, or workplanes in the public API.
- Give the agent stable semantic references for where to attach limbs and place
  features.
- Preserve B-rep structure internally until the end of the pipeline.
- Return native `MeshGeometry` at the public boundary.

## Non-goals

- Do not expose OCCT or CadQuery objects directly.
- Do not require users to name raw face IDs or edge IDs.
- Do not replace `section_loft(...)` for simple one-body shell authoring.
- Do not promise exact parametric-history replay in the public API.

## Core Design Idea

Introduce a new "feature body" layer that sits above individual lofts, sweeps,
and booleans.

The key abstraction is:

- author a small number of named body primitives
- define semantic attachment frames on those primitives
- join primitives together with declarative continuity/blend intent
- add local features relative to semantic frames or regions
- keep everything as kernel solids/shells until the final tessellation step

This is a better fit for an agent than raw kernel topology because the agent can
reason about:

- trunk vs limb
- top/front/side of a body
- station along a body
- attachment location on a section
- local sketch frame for a cut or emboss

without needing to reason about unstable face indexing after healing.

## Proposed Public Surface

The current `section_loft(...)` surface should remain as the simple direct path.

The planned extension should be a separate family, tentatively:

```python
from sdk import (
    FeatureBodySpec,
    LoftBody,
    SweepBody,
    RevolveBody,
    AttachFrame,
    BranchJoin,
    PocketFeature,
    SlotFeature,
    BossFeature,
    SeamFeature,
    FilletFeature,
    build_feature_body,
)
```

Primary entrypoint:

```python
build_feature_body(spec: FeatureBodySpec, /, **overrides) -> MeshGeometry
```

This keeps the public contract simple:

- input: declarative body specification
- output: final `MeshGeometry`

Internally, the implementation should preserve an opaque kernel-body graph until
all joins and local features have been applied.

## Proposed Spec Shape

```python
FeatureBodySpec(
    bodies=[...],
    joins=[...],
    features=[...],
    symmetry=None,
    heal="auto",
    tessellation=LoftTessellation(),
)
```

### `bodies`

Each body is a named primary solid or shell candidate.

Planned body types:

- `LoftBody`
- `SweepBody`
- `ExtrudeBody`
- `RevolveBody`

These are not raw OCCT wrappers. They are sparse authored specs similar in
spirit to `SectionLoftSpec`.

Example sketch:

```python
LoftBody(
    name="main_shell",
    sections=[...],
    path=None,
    symmetry="mirror_yz",
)
```

```python
SweepBody(
    name="handle",
    profile=rounded_rect_profile(...),
    path=[...],
)
```

### `joins`

Joins define how one body attaches to another.

Planned join types:

- `FuseJoin`: simple fuse without explicit blend intent
- `BranchJoin`: child limb attaches to parent body at a semantic frame
- `BridgeJoin`: connect two attachment frames with a transitional body
- `BlendJoin`: request tangent or curvature continuity across the junction

The important point is that joins reference semantic frames, not raw faces.

### `features`

Features are localized operations performed after the main bodies exist.

Planned feature types:

- `PocketFeature`: recessed cut normal to a local frame
- `SlotFeature`: elongated opening or wheel slot
- `BossFeature`: raised pad or post
- `SeamFeature`: shallow split or visual seam
- `RibFeature`: support rib or ridge
- `FilletFeature`: smoothing pass over a semantic region
- `TrimFeature`: trim/split/remove a local region with a profile or plane

These features are intended to cover the most common "one local hard thing on a
soft body" cases without requiring explicit low-level boolean choreography in
generated code.

## Semantic Frames Instead of Topology Selectors

This is the main abstraction that should make the API work well for the agent.

The public API should let the model select locations by stable semantic frames
derived from the authored primitive, not by face handles created after kernel
healing.

Tentative attachment-frame form:

```python
AttachFrame(
    body="main_shell",
    station=0.42,
    around="right",
    inset=0.0,
    normal="outward",
)
```

Where:

- `body` selects the named source body
- `station` is normalized progress along the loft/sweep path or section stack
- `around` identifies a semantic side or perimeter landmark
- `inset` offsets inward or outward from the local surface
- `normal` picks the default frame orientation

Supported `around` modes should be semantic and finite, for example:

- `top`
- `bottom`
- `left`
- `right`
- `front`
- `rear`
- `u:<float>` for explicit perimeter position when needed

For loft bodies, these frames can be computed from:

- section centroid
- section perimeter landmarks
- path tangent or section-stack tangent
- mirrored frame conventions when symmetry is active

For sweeps, they can be computed from:

- path tangent
- profile frame
- explicit up-vector or guide curve when needed

This avoids the failure mode where a boolean or healing step changes the face
ordering and invalidates later references.

## Example 1: Mug With Integrated Handle

Conceptually:

```python
geom = build_feature_body(
    FeatureBodySpec(
        bodies=[
            LoftBody(name="cup", sections=[...]),
            SweepBody(name="handle", profile=rounded_rect_profile(...), path=[...]),
        ],
        joins=[
            BranchJoin(
                parent="cup",
                child="handle",
                start=AttachFrame(body="cup", station=0.30, around="right"),
                end=AttachFrame(body="cup", station=0.72, around="right"),
                continuity="tangent",
                blend_radius=0.008,
            ),
        ],
    )
)
```

The agent should not need to manually:

- union the handle into the cup
- guess which cup face to trim
- guess where to fillet the contact patch

Those are consequences of the declared join intent.

## Example 2: Kettle Body With Spout

Conceptually:

- loft the main vessel body
- create a sweep body for the spout
- attach the spout to a side frame near the upper front quadrant
- request a tangent branch join
- optionally add a lid recess and a handle mount boss as local features

This is the first class of object that the new API should unlock cleanly.

## Example 3: Mouse With Hard Local Features

Even when branching is not needed, the same API should help with localized hard
features:

- wheel slot
- button split seam
- thumb pocket
- underside sensor recess

That allows the shell to remain a clean loft while the detailed edits become
semantic features instead of ad hoc boolean boxes sprinkled through the model.

## Why Not Just Expose CadQuery Workplanes

CadQuery/OCCT workplanes and face selectors are powerful, but they are not the
right public abstraction for generated code in this repository.

Problems:

- topological naming is unstable after joins, trims, and healing
- generated code becomes verbose and brittle
- the agent has to reason about CAD kernel mechanics instead of object intent
- failure messages become implementation-specific and hard to recover from

The goal here is not to hide kernel power from the implementation. It is to
package that power behind stable, sparse, agent-friendly declarations.

## Internal Architecture

Internally, this should be implemented as a B-rep-first pipeline.

Planned stages:

1. Normalize `FeatureBodySpec`.
2. Build each authored body as an opaque kernel shape plus semantic-frame data.
3. Resolve joins between bodies in kernel space.
4. Apply local features against semantic frames or regions.
5. Heal and sew the resulting shape graph.
6. Tessellate once at the end.
7. Convert to `MeshGeometry`.
8. Apply optional mesh cleanup.

Important internal requirement:

- semantic references must survive healing and body fusion

That likely means carrying authored frame metadata alongside the kernel shape
graph rather than trying to rediscover intent from faces after the fact.

## Planned Region and Feature Selectors

Some features will need broader selection than one exact frame.

Tentative selector families:

- `BodyRegion(body="main", side="top", station_range=(0.2, 0.5))`
- `NearFrame(frame=..., radius=...)`
- `SymmetricPair(frame=..., mirror="yz")`
- `TerminalRegion(body="spout", which="start" | "end")`

These selectors should remain semantic and bounded. Avoid raw query languages,
arbitrary selector strings, or direct kernel predicates in the public API.

## Relationship To Existing APIs

### Keep

- `section_loft(...)` for single-shell exterior forms
- `repair_loft(...)` for sparse section cleanup
- wire and sweep helpers for standalone rails, tubes, and trim
- mesh booleans for low-level fallback work

### Add

- `build_feature_body(...)` for multi-body shell composition
- semantic attachment frames
- local body features
- join continuity and blend intent

### Do Not Replace Immediately

The new family should complement the current loft helpers, not invalidate them.

Practical guidance:

- if the object is one continuous shell: use `section_loft(...)`
- if the object is one continuous tube/rail: use wire/sweep helpers
- if the object has limbs, join patches, or multiple localized edits: use the
  feature-body API

## First Implementation Slice

The first slice should stay small and solve one real class of objects well.

Recommended v1 scope:

- `FeatureBodySpec`
- `LoftBody`
- `SweepBody`
- `AttachFrame`
- `BranchJoin`
- `PocketFeature`
- `SlotFeature`
- `SeamFeature`
- one final `build_feature_body(...)` entrypoint

That is enough to cover:

- mugs with handles
- kettles with spouts
- watering cans with handles/spouts
- game-controller grip branches
- mouse-like shells with wheel slots and seams

## Deferred Work

Defer these until the first slice is stable:

- arbitrary face/edge selection
- shell-thickness editing
- generalized sketch-on-surface workflows
- complex draft and offset-shell features
- full parametric history editing
- user-visible exposure of kernel-body intermediate objects

## Suggested Testing Plan

When this moves from design to implementation, add coverage for:

- branching join between a loft body and sweep body
- mirrored dual-branch object
- localized pocket/slot/seam placement by semantic frame
- stable behavior after healing and final tessellation
- failure messages when an attachment frame is invalid or underspecified

Representative objects:

- mug with integrated handle
- kettle with side spout
- watering can with top handle and front spout
- game controller half-shell with grip branch

## Open Questions

- Should the public output remain only `MeshGeometry`, or should there also be a
  non-exported internal `KernelBodyResult` to improve debugging?
- Should `AttachFrame` be section-driven only, or also allow explicit anchor
  curves and planes?
- How much automatic blend behavior should be implicit in `BranchJoin` versus
  expressed as a separate `BlendJoin`?
- Should localized features default to symmetric application when the parent
  body has mirror symmetry?

## Recommendation

Implement this as a new family beside `section_loft(...)`, not as a mutation of
`SectionLoftSpec`.

`SectionLoftSpec` should remain the small abstraction for one authored shell.
The new feature-body family should own:

- multi-body composition
- branch attachments
- semantic join intent
- localized hard features

That separation keeps the current loft surface simple while creating a realistic
path toward mugs, kettles, watering cans, and controller-like objects.
