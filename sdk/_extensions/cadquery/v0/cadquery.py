from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from sdk._core.v0.assets import AssetContextLike, resolve_asset_context
from sdk._core.v0.types import Mesh
from sdk._dependencies import require_cadquery

Vec3 = tuple[float, float, float]
AABB = tuple[Vec3, Vec3]
_CADQUERY_MESH_CACHE_VERSION = "v1"


@dataclass(frozen=True)
class CadQueryMeshExport:
    mesh: Mesh
    mesh_path: Path
    local_aabb: AABB
    center_xyz: Vec3
    size_xyz: Vec3


@dataclass(frozen=True)
class _CadQueryMeshCacheMetadata:
    cache_key: str
    local_aabb: AABB


def _require_cadquery() -> Any:
    return require_cadquery(feature="CadQuery support in `sdk_hybrid`")


def _vector_xyz(value: Any) -> Vec3:
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return (float(value.x), float(value.y), float(value.z))
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    raise TypeError(f"Unsupported CadQuery vertex type: {type(value).__name__}")


def _coerce_shape(model: object, cq: Any) -> object:
    if isinstance(model, cq.Assembly):
        try:
            return model.toCompound()
        except Exception as exc:
            raise TypeError("Failed to convert CadQuery Assembly into a compound shape") from exc

    if isinstance(model, cq.Workplane):
        try:
            values = list(model.vals())
        except Exception as exc:
            raise TypeError("CadQuery Workplane did not produce an exportable shape") from exc
        if not values:
            raise TypeError("CadQuery Workplane produced no exportable shape")
        if not all(isinstance(value, cq.Shape) for value in values):
            raise TypeError("CadQuery Workplane produced non-shape objects")
        if len(values) == 1:
            return values[0]
        try:
            return cq.Compound.makeCompound(values)
        except Exception as exc:
            raise TypeError(
                "Failed to combine CadQuery Workplane objects into a compound shape"
            ) from exc

    if isinstance(model, cq.Shape):
        return model

    raise TypeError(
        "Unsupported CadQuery model type. Expected cadquery.Shape, "
        "cadquery.Workplane, or cadquery.Assembly."
    )


def _tessellate_cadquery_shape(
    shape: object,
    *,
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
    unit_scale: float = 1.0,
) -> tuple[list[Vec3], list[tuple[int, int, int]]]:
    try:
        vertices_raw, triangles_raw = shape.tessellate(
            float(tolerance),
            float(angular_tolerance),
        )
    except TypeError:
        vertices_raw, triangles_raw = shape.tessellate(float(tolerance))

    scale = float(unit_scale)
    vertices = [tuple(coord * scale for coord in _vector_xyz(vertex)) for vertex in vertices_raw]
    triangles = [(int(face[0]), int(face[1]), int(face[2])) for face in triangles_raw]

    if not vertices:
        raise ValueError("CadQuery tessellation produced no vertices")
    if not triangles:
        raise ValueError("CadQuery tessellation produced no faces")

    return vertices, triangles


def tessellate_cadquery(
    model: object,
    *,
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
    unit_scale: float = 1.0,
) -> tuple[list[Vec3], list[tuple[int, int, int]]]:
    cq = _require_cadquery()
    shape = _coerce_shape(model, cq)
    return _tessellate_cadquery_shape(
        shape,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        unit_scale=unit_scale,
    )


def _export_friendly_mesh_filename(filename: str) -> str:
    if not isinstance(filename, str) or not filename:
        return filename

    normalized = filename.replace("\\", "/")
    if normalized.startswith("assets/meshes/"):
        return normalized
    if normalized.startswith("meshes/"):
        return normalized

    try:
        path = Path(filename)
    except Exception:
        return filename

    parts = list(path.parts)
    asset_meshes_indices = [
        i for i in range(len(parts) - 1) if parts[i] == "assets" and parts[i + 1] == "meshes"
    ]
    if asset_meshes_indices:
        return Path(*parts[asset_meshes_indices[-1] :]).as_posix()

    meshes_indices = [i for i, part in enumerate(parts) if part == "meshes"]
    if not meshes_indices:
        return filename

    return Path(*parts[meshes_indices[-1] :]).as_posix()


def _resolve_export_path(
    filename: str | os.PathLike[str],
    *,
    assets: AssetContextLike | None,
) -> Path:
    path = Path(filename)
    asset_ctx = resolve_asset_context(assets)
    if asset_ctx is not None and not path.is_absolute():
        return asset_ctx.mesh_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _cache_root_for_export(
    mesh_path: Path,
    *,
    assets: AssetContextLike | None,
) -> Path:
    asset_ctx = resolve_asset_context(assets)
    if asset_ctx is not None:
        return asset_ctx.asset_root / "assets" / ".cadquery_cache"
    return mesh_path.parent / ".cadquery_cache"


def _cache_mesh_path(cache_root: Path, cache_key: str) -> Path:
    return cache_root / f"{cache_key}.obj"


def _cache_metadata_path(cache_root: Path, cache_key: str) -> Path:
    return cache_root / f"{cache_key}.json"


def _export_metadata_path(mesh_path: Path) -> Path:
    return Path(f"{mesh_path.as_posix()}.cadquery.json")


def _coerce_vec3(value: Any) -> Vec3 | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return None


def _parse_cache_metadata(payload: Any) -> _CadQueryMeshCacheMetadata | None:
    if not isinstance(payload, dict):
        return None
    cache_key = payload.get("cache_key")
    local_aabb = payload.get("local_aabb")
    if not isinstance(cache_key, str) or not cache_key.strip():
        return None
    if not isinstance(local_aabb, (list, tuple)) or len(local_aabb) != 2:
        return None
    local_min = _coerce_vec3(local_aabb[0])
    local_max = _coerce_vec3(local_aabb[1])
    if local_min is None or local_max is None:
        return None
    return _CadQueryMeshCacheMetadata(
        cache_key=cache_key,
        local_aabb=(local_min, local_max),
    )


def _read_cache_metadata(path: Path) -> _CadQueryMeshCacheMetadata | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _parse_cache_metadata(payload)


def _write_cache_metadata(path: Path, metadata: _CadQueryMeshCacheMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cache_key": metadata.cache_key,
        "local_aabb": [
            list(metadata.local_aabb[0]),
            list(metadata.local_aabb[1]),
        ],
        "version": _CADQUERY_MESH_CACHE_VERSION,
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _serialize_shape_for_cache(shape: object) -> bytes:
    for exporter_name in ("exportBin", "exportBrep"):
        exporter = getattr(shape, exporter_name, None)
        if not callable(exporter):
            continue
        buffer = BytesIO()
        try:
            exporter(buffer)
        except Exception:
            continue
        payload = buffer.getvalue()
        if payload:
            return payload
    raise ValueError("CadQuery shape could not be serialized for cache key generation")


def _cadquery_mesh_cache_key(
    shape: object,
    *,
    tolerance: float,
    angular_tolerance: float,
    unit_scale: float,
    cq: Any,
) -> str:
    digest = hashlib.sha256()
    digest.update(_CADQUERY_MESH_CACHE_VERSION.encode("utf-8"))
    digest.update(
        json.dumps(
            {
                "angular_tolerance": float(angular_tolerance),
                "cadquery_version": str(getattr(cq, "__version__", "")),
                "tolerance": float(tolerance),
                "unit_scale": float(unit_scale),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    digest.update(b"\0")
    digest.update(_serialize_shape_for_cache(shape))
    return digest.hexdigest()


def _copy_cached_mesh(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _write_obj(
    path: Path,
    *,
    vertices: list[Vec3],
    triangles: list[tuple[int, int, int]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for x, y, z in vertices:
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    for a, b, c in triangles:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _local_aabb_from_vertices(vertices: list[Vec3]) -> AABB:
    mn = (
        min(v[0] for v in vertices),
        min(v[1] for v in vertices),
        min(v[2] for v in vertices),
    )
    mx = (
        max(v[0] for v in vertices),
        max(v[1] for v in vertices),
        max(v[2] for v in vertices),
    )
    return mn, mx


def _aabb_center(aabb: AABB) -> Vec3:
    (mn, mx) = aabb
    return (
        (float(mn[0]) + float(mx[0])) * 0.5,
        (float(mn[1]) + float(mx[1])) * 0.5,
        (float(mn[2]) + float(mx[2])) * 0.5,
    )


def _aabb_size(aabb: AABB) -> Vec3:
    (mn, mx) = aabb
    return (
        float(mx[0]) - float(mn[0]),
        float(mx[1]) - float(mn[1]),
        float(mx[2]) - float(mn[2]),
    )


def cadquery_local_aabb(
    model: object,
    *,
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
    unit_scale: float = 1.0,
) -> AABB:
    vertices, _triangles = tessellate_cadquery(
        model,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        unit_scale=unit_scale,
    )
    return _local_aabb_from_vertices(vertices)


def export_cadquery_mesh(
    model: object,
    filename: str | os.PathLike[str],
    *,
    assets: AssetContextLike | None = None,
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
    unit_scale: float = 1.0,
) -> CadQueryMeshExport:
    asset_ctx = resolve_asset_context(assets)
    path = _resolve_export_path(filename, assets=asset_ctx)
    cq = _require_cadquery()
    shape = _coerce_shape(model, cq)
    cache_key = _cadquery_mesh_cache_key(
        shape,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        unit_scale=unit_scale,
        cq=cq,
    )
    destination_metadata_path = _export_metadata_path(path)
    destination_metadata = _read_cache_metadata(destination_metadata_path)
    if (
        path.exists()
        and destination_metadata is not None
        and destination_metadata.cache_key == cache_key
    ):
        local_aabb = destination_metadata.local_aabb
        return CadQueryMeshExport(
            mesh=Mesh(filename=_export_friendly_mesh_filename(path.as_posix())),
            mesh_path=path,
            local_aabb=local_aabb,
            center_xyz=_aabb_center(local_aabb),
            size_xyz=_aabb_size(local_aabb),
        )

    cache_root = _cache_root_for_export(path, assets=asset_ctx)
    cache_mesh_path = _cache_mesh_path(cache_root, cache_key)
    cache_metadata_path = _cache_metadata_path(cache_root, cache_key)
    cached_metadata = _read_cache_metadata(cache_metadata_path)
    if (
        cache_mesh_path.exists()
        and cached_metadata is not None
        and cached_metadata.cache_key == cache_key
    ):
        _copy_cached_mesh(cache_mesh_path, path)
        _write_cache_metadata(destination_metadata_path, cached_metadata)
        local_aabb = cached_metadata.local_aabb
        return CadQueryMeshExport(
            mesh=Mesh(filename=_export_friendly_mesh_filename(path.as_posix())),
            mesh_path=path,
            local_aabb=local_aabb,
            center_xyz=_aabb_center(local_aabb),
            size_xyz=_aabb_size(local_aabb),
        )

    vertices, triangles = _tessellate_cadquery_shape(
        shape,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        unit_scale=unit_scale,
    )
    _write_obj(cache_mesh_path, vertices=vertices, triangles=triangles)
    local_aabb = _local_aabb_from_vertices(vertices)
    metadata = _CadQueryMeshCacheMetadata(cache_key=cache_key, local_aabb=local_aabb)
    _write_cache_metadata(cache_metadata_path, metadata)
    _copy_cached_mesh(cache_mesh_path, path)
    _write_cache_metadata(destination_metadata_path, metadata)
    return CadQueryMeshExport(
        mesh=Mesh(filename=_export_friendly_mesh_filename(path.as_posix())),
        mesh_path=path,
        local_aabb=local_aabb,
        center_xyz=_aabb_center(local_aabb),
        size_xyz=_aabb_size(local_aabb),
    )


def save_cadquery_obj(
    model: object,
    filename: str | os.PathLike[str],
    *,
    assets: AssetContextLike | None = None,
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
    unit_scale: float = 1.0,
) -> Path:
    export = export_cadquery_mesh(
        model,
        filename,
        assets=assets,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        unit_scale=unit_scale,
    )
    return export.mesh_path


def mesh_from_cadquery(
    model: object,
    filename: str | os.PathLike[str],
    *,
    assets: AssetContextLike | None = None,
    tolerance: float = 0.001,
    angular_tolerance: float = 0.1,
    unit_scale: float = 1.0,
) -> Mesh:
    export = export_cadquery_mesh(
        model,
        filename,
        assets=assets,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        unit_scale=unit_scale,
    )
    return export.mesh
