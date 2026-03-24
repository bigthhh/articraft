# Probe Tooling

`probe_model` is an inspection-only debugging tool for running a short Python snippet against the current bound `model.py`.
Use it when placements, containment, overlap risk, support, or articulation behavior are uncertain and you need measurements or better geometry intuition before editing code.

`probe_model` does not create persistent guarantees by itself.
Use it to learn what the current model is doing, then encode the lasting regression in `run_tests()`, because those checks persist across repair turns.

Prefer object-first probe snippets.
Resolve the relevant parts, articulations, and named visuals into locals once, then pass those objects into `pair_report(...)`, `contact_report(...)`, `gap_report(...)`, and related helpers instead of repeating raw string lookups throughout the snippet.

## Call contract

Tool parameters:

- `code: str`
  Python snippet to execute. Write ordinary Python code and call `emit(value)` exactly once.
- `timeout_ms: int = 10000`
  Maximum runtime in milliseconds. Use a larger timeout only when pose sampling or repeated pair checks genuinely need it.
- `include_stdout: bool = False`
  When `True`, captured `print(...)` output and stderr are included in the tool result for debugging.

Execution rules:

- Do not pass `file_path`; the harness binds the tool to the current target file.
- `emit(value)` must be called exactly once.
- `value` must be JSON-serializable.
- `print(...)` is allowed for debugging, but it is secondary to the emitted result.
- The snippet runs in an isolated subprocess with a timeout.
- Use the tool only for non-mutating inspection. Do not write files, modify `object_model`, launch subprocesses, access the network, or perform destructive actions.

Typical result shape:

- Success returns an object with `ok: true`, the emitted `result`, and timing metadata.
- Failures return `ok: false` plus an `error` object such as lookup failure, timeout, snippet exception, missing `emit(...)`, or non-serializable output.

## Preloaded names

The snippet runs with these names already available:

- `object_model`
  The current articulated object returned by `build_object_model()`.
- `ctx`
  The active `TestContext`-style helper bound to the same `object_model`.
- `emit(value)`
  Records the one required JSON-serializable result payload.
- `catalog()`
  Returns the helper catalog grouped into `core`, `measurement`, and `review`.

## Lookup and pose helpers

### `pose(mapping: dict[str, float] | None = None, **kwargs: float) -> ContextManager`

Temporarily applies articulation positions for pose-aware inspection.

- Accepts articulation-name keys and numeric positions.
- Supports either a mapping, keyword arguments, or both.
- Returns a context manager for `with pose(...): ...`.

Example:

```python
with pose({"lid_hinge": 1.0}):
    emit(contact_report(part("lid"), part("frame")))
```

### `part(name: str) -> object`

Returns the named part from `object_model`.

- Accepts a part name string.
- Raises a lookup error if the part does not exist.

### `joint(name: str) -> object`

Returns the named articulation from `object_model`.

- Accepts an articulation name string.
- Raises a lookup error if the articulation does not exist.

### `visual(part_name: str, visual_name: str) -> object`

Returns a named visual that belongs to a specific part.

- Accepts the owning part name and visual name.
- Raises a lookup error if either lookup fails.

### `parts() -> list[object]`

Returns all parts in the current object model.

### `joints() -> list[object]`

Returns all articulations in the current object model.

### `visuals(part_or_name: object) -> list[object]`

Returns all visuals for a part.

- Accepts a part object, a part name string, or a visual whose owning part should be resolved.
- Returns the part's visual list.

### `name(obj: object) -> str`

Returns a readable name for a part, articulation, or visual.

- For visuals, the result includes the owning part when needed.
- Useful when building your own emitted debug structures.

## Measurement helpers

Measurement helpers accept a part object, visual object, or compatible named lookup result unless noted otherwise.

### `aabb(obj: object) -> dict[str, list[float]] | None`

Returns the world-space axis-aligned bounding box for a part or visual.

- Result shape: `{"min": [x, y, z], "max": [x, y, z]}`.
- Returns `None` when no measurable world-space bounds are available.

### `dims(obj: object) -> list[float] | None`

Returns exact projection-derived world-space dimensions as `[dx, dy, dz]`.

- Uses exact visual geometry when available.
- This is not the same as `aabb(...)` for rotated cylinders or meshes.

### `center(obj: object) -> list[float] | None`

Returns the exact projection-derived world-space center as `[x, y, z]`.

- Uses exact visual geometry when available.

### `position(obj: object) -> list[float] | None`

Returns a representative world position.

- For parts, this is the part world position from the context.
- For visuals, this is the exact projection-derived visual center.
- For articulations, this is the articulation origin position when available.

### `projection(obj: object, axis_or_axes: str | Sequence[str]) -> dict[str, object]`

Returns exact geometry projection intervals along one or more axes.

- `axis_or_axes` may be `"x"`, `"y"`, `"z"`, `"xy"`, `"xz"`, `"yz"`, or a sequence like `["x", "z"]`.
- Result shape includes the target reference, `metric_kind: "exact_projection"`, and per-axis intervals.

### `summary(obj: object) -> dict[str, object]`

Returns a compact structured summary.

- For parts: kind, name, parent part when applicable, position, center, dims, aabb, and visual names.
- For visuals: kind, name, parent part, and the same measurable fields.
- For articulations: kind, name, type, axis, and motion-limit fields.

## Pair and relationship reports

These helpers return structured dictionaries intended for direct `emit(...)` use.

### `pair_report(a: object, b: object, elem_a: object | None = None, elem_b: object | None = None) -> dict[str, object]`

Returns exact pairwise distance and axis projections for two targets.

- `a` and `b` may be parts or visuals.
- `elem_a` and `elem_b` optionally narrow each side to a specific local visual.
- Result includes target refs, `collided`, `min_distance`, per-axis intervals, signed gaps, overlaps, and optional center delta.

### `gap_report(positive: object, negative: object, axis: str, positive_elem: object | None = None, negative_elem: object | None = None) -> dict[str, object]`

Measures the signed directional gap along one axis.

- `axis` must resolve to one of `"x"`, `"y"`, or `"z"`.
- Positive values mean separation; negative values mean penetration.
- Result includes `gap` plus the compared projection intervals.

### `overlap_report(a: object, b: object, axes: str | Sequence[str] = "xy", elem_a: object | None = None, elem_b: object | None = None) -> dict[str, object]`

Summarizes projection overlap across one or more axes.

- Result includes per-axis overlap values and `min_overlap`.

### `within_report(inner: object, outer: object, axes: str | Sequence[str] = "xy", inner_elem: object | None = None, outer_elem: object | None = None) -> dict[str, object]`

Checks whether one target stays within another across the requested axes.

- Result includes overall `within` plus per-axis lower and upper margins.

### `contact_report(a: object, b: object, elem_a: object | None = None, elem_b: object | None = None, contact_tol: float = 1e-6) -> dict[str, object]`

Determines whether two targets should be treated as contacting.

- Uses exact pair distance and collision state.
- Result includes `contact`, `contact_tol`, `min_distance`, and `collided`.

### `mount_report(child: object, parent: object, elem_a: object | None = None, elem_b: object | None = None) -> dict[str, object]`

Returns a mounting-oriented review for a child relative to a parent.

- Combines exact pair data, XY containment, Z gap, and center offset.
- Result includes `looks_mounted` plus the underlying `within_xy`, `gap_z`, and `pair` reports.

### `containment_report(inner: object, outer: object, axes: str | Sequence[str] = "xy") -> dict[str, object]`

Alias-style containment review that currently delegates to `within_report(...)`.

### `alignment_report(a: object, b: object) -> dict[str, object]`

Returns center-to-center alignment information.

- Result includes signed `delta` and absolute `abs_delta` in world space.

## Review helpers

These are broader diagnostic helpers that summarize multiple measurements at once.

### `sample_poses(max_samples: int = 32, seed: int = 0) -> list[dict[str, float]]`

Returns articulation pose samples generated from the current object model.

- Each item is a mapping from articulation name to sampled position.
- Useful for building your own repeated pose probes.

### `nearest_neighbors(obj: object, candidates: Iterable[object] | None = None, limit: int = 5) -> list[dict[str, object]]`

Returns the closest candidate parts relative to a target.

- Defaults to all other parts when `candidates` is omitted.
- Results are sorted with collisions first, then by minimum distance.
- Each item includes target ref, candidate ref, collision state, minimum distance, and axis gaps.

### `find_clearance_risks(limit: int = 10, parts: Iterable[object] | None = None) -> list[dict[str, object]]`

Scans part pairs for likely collision or clearance issues.

- Defaults to all parts.
- Results are sorted with collisions first, then by minimum distance.

### `find_floating_parts(limit: int = 10, parts: Iterable[object] | None = None) -> list[dict[str, object]]`

Flags parts whose nearest neighbor suggests they may read as floating.

- Each item includes the part ref, its nearest neighbor summary, and a `suspicious` boolean.

### `layout_report(items: Iterable[object], axis: str = "x") -> dict[str, object]`

Reviews repeated spacing along one axis.

- Requires measurable centers.
- Result includes ordered items, span, pitches, pitch statistics, and outlier indices.

### `grid_report(items: Iterable[object], axes: str | Sequence[str] = "xy") -> dict[str, object]`

Reviews whether items form an approximate 2D grid.

- Requires exactly two axes.
- Result includes inferred row and column counts plus coordinate clusters.

### `symmetry_report(items: Iterable[object], axis: str = "x") -> dict[str, object]`

Reviews approximate bilateral symmetry across one axis.

- Result includes inferred midplane, mirrored pairs, unmatched items, and the worst mirror offset.

## Practical examples

Mounted feature review:

```python
panel = part("panel")
knob = visual("panel", "knob")
emit(mount_report(knob, panel))
```

Pose-aware contact check:

```python
with pose(lid_hinge=1.0):
    emit(contact_report(part("lid"), part("frame")))
```

Repeated layout review:

```python
keys = [visual("keyboard", name) for name in ("key_1", "key_2", "key_3", "key_4")]
emit(layout_report(keys, axis="x"))
```

Nearest-clearance scan:

```python
emit(find_clearance_risks(limit=5))
```

Known should-not-overlap pair:

```python
base = part("base")
bowl = part("bowl")
column_shell = visual("base", "column_shell")
bowl_shell = visual("bowl", "bowl_shell")
emit(pair_report(bowl, base, elem_a=bowl_shell, elem_b=column_shell))
```
