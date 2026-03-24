from __future__ import annotations

from textwrap import dedent

CORE_HELPERS = (
    "`object_model`, `ctx`, `emit(value)`, `pose(mapping)`",
    "`part(name)`, `joint(name)`, `visual(part_name, visual_name)`",
    "`parts()`, `joints()`, `visuals(part_or_name)`, `name(obj)`",
)

MEASUREMENT_HELPERS = (
    "`aabb(obj)`, `dims(obj)`, `center(obj)`, `position(obj)`, `projection(obj, axis_or_axes)`",
    "`summary(obj)`",
    "`pair_report(a, b, elem_a=None, elem_b=None)`",
    "`gap_report(positive, negative, axis, positive_elem=None, negative_elem=None)`",
    "`overlap_report(a, b, axes='xy', elem_a=None, elem_b=None)`",
    "`within_report(inner, outer, axes='xy', inner_elem=None, outer_elem=None)`",
    "`contact_report(a, b, elem_a=None, elem_b=None, contact_tol=1e-6)`",
    "`mount_report(child, parent, elem_a=None, elem_b=None)`",
    "`containment_report(inner, outer, axes='xy')`, `alignment_report(a, b)`",
)

REVIEW_HELPERS = (
    "`sample_poses(max_samples=32, seed=0)`",
    "`nearest_neighbors(obj, candidates=None, limit=5)`",
    "`find_clearance_risks(limit=10, parts=None)`",
    "`find_floating_parts(limit=10, parts=None)`",
    "`layout_report(items, axis='x')`, `grid_report(items, axes='xy')`, `symmetry_report(items, axis='x')`",
    "`catalog()` returns the helper catalog as structured data.",
)


def build_probe_model_description() -> str:
    return dedent(
        f"""
        Execute a short Python snippet against the current bound `model.py` for inspection-only geometry diagnosis.

        This tool is intended for inspection-only use and is bound to one target file by the harness.
        Do not pass file paths. Use it when placements, clearances, containment, overlap risk,
        or pose behavior are uncertain.

        Execution contract:
        - Write ordinary Python code.
        - Use this tool only for non-mutating inspection and measurement.
        - `emit(value)` must be called exactly once.
        - `value` must be JSON-serializable.
        - `print(...)` is allowed for debugging only. It is captured separately and returned only when requested.
        - Do not write files, modify `object_model`, launch subprocesses, access the network, or perform destructive actions.
        - The snippet runs in an isolated subprocess with a timeout.

        Preloaded names:
        - Core:
          - {CORE_HELPERS[0]}
          - {CORE_HELPERS[1]}
          - {CORE_HELPERS[2]}
        - Measurement:
          - {MEASUREMENT_HELPERS[0]}
          - {MEASUREMENT_HELPERS[1]}
          - {MEASUREMENT_HELPERS[2]}
          - {MEASUREMENT_HELPERS[3]}
          - {MEASUREMENT_HELPERS[4]}
          - {MEASUREMENT_HELPERS[5]}
          - {MEASUREMENT_HELPERS[6]}
        - Review:
          - {REVIEW_HELPERS[0]}
          - {REVIEW_HELPERS[1]}
          - {REVIEW_HELPERS[2]}
          - {REVIEW_HELPERS[3]}
          - {REVIEW_HELPERS[4]}
          - {REVIEW_HELPERS[5]}

        Guidance:
        - Lookup helpers accept strings and return resolved model objects.
        - Report helpers return compact dictionaries with raw measurements and evidence types.
        - These helpers are tool-local review conveniences built on the current `object_model` and `TestContext`.
        - They are not part of the public SDK API and may use internal exact-geometry helpers.

        Example: mounted-part review
        ```python
        knob = visual("panel", "knob")
        panel = part("panel")
        emit(mount_report(knob, panel))
        ```

        Example: repeated layout review
        ```python
        keys = [visual("keyboard", name) for name in ("key_1", "key_2", "key_3", "key_4")]
        emit(layout_report(keys, axis="x"))
        ```

        Example: nearest-clearance scan
        ```python
        emit(find_clearance_risks(limit=5))
        ```
        """
    ).strip()


PROBE_MODEL_DESCRIPTION = build_probe_model_description()
