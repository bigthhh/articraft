from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sdk import ArticulatedObject, Box, Origin, find_geometry_overlaps
from sdk._core.v0 import geometry_qc
from sdk._core.v0.types import Collision


def _build_disjoint_collision_model() -> ArticulatedObject:
    model = ArticulatedObject(name="disjoint_collision_parts")

    left = model.part("left")
    left.collisions.append(
        Collision(
            geometry=Box((0.1, 0.1, 0.1)),
            origin=Origin(xyz=(0.0, 0.0, 0.05)),
            name="left_box",
        )
    )

    right = model.part("right")
    right.collisions.append(
        Collision(
            geometry=Box((0.1, 0.1, 0.1)),
            origin=Origin(xyz=(1.0, 0.0, 0.05)),
            name="right_box",
        )
    )

    return model


def test_collision_overlap_qc_prunes_disjoint_aabbs_before_fcl(
    monkeypatch: object,
) -> None:
    calls = {"collide": 0}

    class FakeCollisionRequest:
        pass

    class FakeCollisionResult:
        pass

    def fake_collide(*_args: object, **_kwargs: object) -> int:
        calls["collide"] += 1
        raise AssertionError("fcl.collide should not run when AABB overlap thresholds fail")

    fake_fcl = types.SimpleNamespace(
        CollisionRequest=FakeCollisionRequest,
        CollisionResult=FakeCollisionResult,
        collide=fake_collide,
    )

    monkeypatch.setitem(sys.modules, "fcl", fake_fcl)
    monkeypatch.setattr(
        geometry_qc,
        "compile_object_model_with_generated_collisions",
        lambda model, asset_root=None: model,
    )
    monkeypatch.setattr(
        geometry_qc,
        "_collision_object_from_geometry",
        lambda geometry, **kwargs: object(),
    )

    overlaps = find_geometry_overlaps(
        _build_disjoint_collision_model(),
        geometry_source="collision",
        max_pose_samples=1,
        overlap_tol=1e-3,
        overlap_volume_tol=0.0,
    )

    assert overlaps == []
    assert calls["collide"] == 0


def test_load_fcl_mesh_rejects_obj_without_triangles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh_path = tmp_path / "empty_faces.obj"
    mesh_path.write_text(
        "\n".join(
            [
                "v 0 0 0",
                "v 1 0 0",
                "v 0 1 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    fake_fcl = types.SimpleNamespace(BVHModel=lambda: object())
    monkeypatch.setitem(sys.modules, "fcl", fake_fcl)

    class FakeTrimesh:
        def __init__(self) -> None:
            self.vertices = types.SimpleNamespace(size=9)
            self.faces = types.SimpleNamespace(size=0)

    fake_trimesh = types.SimpleNamespace(
        Trimesh=FakeTrimesh,
        load_mesh=lambda path, force="mesh": FakeTrimesh(),
    )
    monkeypatch.setitem(sys.modules, "trimesh", fake_trimesh)

    with pytest.raises(geometry_qc.ValidationError, match="no triangles"):
        geometry_qc._load_fcl_mesh(mesh_path, cache={})
