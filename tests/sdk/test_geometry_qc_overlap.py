"""Regression coverage for geometry-QC overlap detection.

This is the safety net that must exist before any overlap/collision performance
optimization: it pins the correctness contract (clear overlaps are reported,
clear gaps are not) so a future speedup cannot silently start missing collisions.
"""

from __future__ import annotations

from sdk import ArticulatedObject, ArticulationType, Box, Origin
from sdk._core.v0.geometry_qc import find_geometry_overlaps


def _two_box_model(*, center_gap: float) -> ArticulatedObject:
    model = ArticulatedObject(name="qc_overlap_fixture")
    material = model.material("grey", rgba=(0.5, 0.5, 0.5, 1.0))
    root = model.part("root")
    root.visual(Box((0.1, 0.1, 0.1)), origin=Origin(xyz=(0.0, 0.0, 0.0)), material=material, name="root_box")
    child = model.part("child")
    child.visual(
        Box((0.1, 0.1, 0.1)),
        origin=Origin(xyz=(center_gap, 0.0, 0.0)),
        material=material,
        name="child_box",
    )
    model.articulation(
        "fixed_joint",
        ArticulationType.FIXED,
        parent=root,
        child=child,
        origin=Origin(xyz=(0.0, 0.0, 0.0)),
        axis=(0.0, 0.0, 1.0),
    )
    return model


def test_overlap_detection_reports_clear_overlap() -> None:
    # Two 0.1 cubes whose centers are 0.05 apart share half their extent.
    overlaps = find_geometry_overlaps(_two_box_model(center_gap=0.05), max_pose_samples=1)
    assert overlaps, "expected the overlapping cubes to be reported"


def test_overlap_detection_passes_clear_gap() -> None:
    # Centers 0.5 apart leaves a 0.4 gap between the 0.1 cubes.
    overlaps = find_geometry_overlaps(_two_box_model(center_gap=0.5), max_pose_samples=1)
    assert overlaps == [], f"expected no overlap for well-separated cubes, got {overlaps}"
