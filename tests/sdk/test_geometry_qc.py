from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sdk import ArticulatedObject, Box, Mesh, Origin, find_geometry_overlaps
from sdk._core.v0 import geometry_qc


def _build_disjoint_collision_model() -> ArticulatedObject:
    model = ArticulatedObject(name="disjoint_collision_parts")

    left = model.part("left")
    left.visual(
        Box((0.1, 0.1, 0.1)),
        origin=Origin(xyz=(0.0, 0.0, 0.05)),
        name="left_box",
    )

    right = model.part("right")
    right.visual(
        Box((0.1, 0.1, 0.1)),
        origin=Origin(xyz=(1.0, 0.0, 0.05)),
        name="right_box",
    )

    return model


def test_collision_overlap_qc_prunes_disjoint_aabbs_before_fcl(
    monkeypatch: pytest.MonkeyPatch,
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
        "_collision_object_from_geometry",
        lambda geometry, **kwargs: object(),
    )

    overlaps = find_geometry_overlaps(
        _build_disjoint_collision_model(),
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
        geometry_qc._load_fcl_mesh(mesh_path, cache={}, scale=None)


def test_collision_object_from_geometry_supports_scaled_meshes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh_relpath = "assets/meshes/scaled.obj"
    mesh_path = tmp_path / mesh_relpath
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh_path.write_text("# placeholder\n", encoding="utf-8")

    applied_scales: list[tuple[float, float, float]] = []

    class FakeArray:
        def __init__(self, values: list[tuple[float, float, float]]) -> None:
            self._values = values
            self.size = len(values) * 3

        def __len__(self) -> int:
            return len(self._values)

    class FakeTrimesh:
        def __init__(self) -> None:
            self.vertices = FakeArray([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
            self.faces = FakeArray([(0, 1, 2)])

        def copy(self) -> "FakeTrimesh":
            return FakeTrimesh()

        def apply_scale(self, scale: tuple[float, float, float]) -> None:
            applied_scales.append(tuple(float(v) for v in scale))

    class FakeBVHModel:
        def beginModel(self, *_args: object) -> None:
            return None

        def addSubModel(self, *_args: object) -> None:
            return None

        def endModel(self) -> None:
            return None

    class FakeTransform:
        def __init__(self, rot: object, trans: object) -> None:
            self.rot = rot
            self.trans = trans

    class FakeCollisionObject:
        def __init__(self, shape: object, transform: object) -> None:
            self.shape = shape
            self.transform = transform

    fake_fcl = types.SimpleNamespace(
        BVHModel=FakeBVHModel,
        CollisionObject=FakeCollisionObject,
        Transform=FakeTransform,
    )
    fake_trimesh = types.SimpleNamespace(
        Trimesh=FakeTrimesh,
        load_mesh=lambda path, force="mesh": FakeTrimesh(),
    )

    monkeypatch.setitem(sys.modules, "fcl", fake_fcl)
    monkeypatch.setitem(sys.modules, "trimesh", fake_trimesh)

    collision_object = geometry_qc._collision_object_from_geometry(
        Mesh(filename=mesh_relpath, scale=(2.0, 3.0, 4.0)),
        elem_tf=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        asset_root=tmp_path,
        mesh_cache={},
    )

    assert isinstance(collision_object, FakeCollisionObject)
    assert applied_scales == [(2.0, 3.0, 4.0)]
