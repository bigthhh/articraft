from __future__ import annotations

import pytest

from sdk_hybrid import cadquery_local_aabb

cq = pytest.importorskip("cadquery")


def test_cadquery_workplane_stack_exports_all_objects() -> None:
    box1 = cq.Workplane("XY").box(1.0, 1.0, 1.0).val()
    box2 = cq.Workplane("XY").center(3.0, 0.0).box(1.0, 1.0, 1.0).val()
    workplane = cq.Workplane("XY").newObject([box1, box2])

    aabb = cadquery_local_aabb(workplane)

    assert aabb == ((-0.5, -0.5, -0.5), (3.5, 0.5, 0.5))
