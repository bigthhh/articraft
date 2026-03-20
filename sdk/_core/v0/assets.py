from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .errors import ValidationError

AssetContextLike = Union["AssetContext", str, Path]
_LEGACY_MESH_PREFIX = "meshes/"


@dataclass(frozen=True)
class AssetContext:
    root: Path
    mesh_subdir: str = "assets/meshes"

    def __post_init__(self) -> None:
        mesh_subdir = str(self.mesh_subdir or "assets/meshes").strip().strip("/\\")
        if not mesh_subdir:
            raise ValueError("mesh_subdir must be non-empty")
        object.__setattr__(self, "root", Path(self.root).resolve())
        object.__setattr__(self, "mesh_subdir", mesh_subdir)

    @classmethod
    def from_script(cls, script_path: str | Path) -> "AssetContext":
        return cls(Path(script_path).resolve().parent)

    @property
    def asset_root(self) -> Path:
        return self.root

    @property
    def mesh_dir(self) -> Path:
        return self.root / self.mesh_subdir

    def ensure_mesh_dir(self) -> Path:
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        return self.mesh_dir

    def mesh_path(
        self,
        filename: str | Path,
        *,
        ensure_dir: bool = True,
    ) -> Path:
        path = Path(filename)
        if not path.is_absolute():
            normalized = path.as_posix()
            if normalized.startswith(f"{self.mesh_subdir}/"):
                path = self.root / path
            elif normalized.startswith(_LEGACY_MESH_PREFIX):
                path = self.mesh_dir / normalized[len(_LEGACY_MESH_PREFIX) :]
            else:
                path = self.mesh_dir / path
        if ensure_dir:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def mesh_ref(self, filename: str | Path) -> str:
        path = Path(filename)
        if path.is_absolute():
            try:
                rel = path.resolve().relative_to(self.root)
            except ValueError:
                return path.as_posix()
        else:
            normalized = path.as_posix()
            if normalized.startswith(f"{self.mesh_subdir}/"):
                rel = path
            elif normalized.startswith(_LEGACY_MESH_PREFIX):
                rel = Path(self.mesh_subdir) / normalized[len(_LEGACY_MESH_PREFIX) :]
            else:
                rel = Path(self.mesh_subdir) / path
        return rel.as_posix()


def coerce_asset_context(value: AssetContextLike | None) -> Optional[AssetContext]:
    if value is None:
        return None
    if isinstance(value, AssetContext):
        return value
    return AssetContext(Path(value))


def resolve_asset_context(
    assets: AssetContextLike | None,
    *owners: object,
) -> Optional[AssetContext]:
    resolved = coerce_asset_context(assets)
    if resolved is not None:
        return resolved

    for owner in owners:
        owner_assets = getattr(owner, "assets", None)
        resolved = coerce_asset_context(owner_assets)
        if resolved is not None:
            return resolved

    return None


def resolve_asset_root(
    asset_root: AssetContextLike | None,
    *owners: object,
) -> Optional[Path]:
    resolved = resolve_asset_context(asset_root, *owners)
    if resolved is not None:
        return resolved.asset_root
    return None


def resolve_mesh_path(
    filename: str | os.PathLike[str],
    *,
    assets: AssetContextLike | None,
    ensure_dir: bool = False,
) -> Path:
    path = Path(filename)
    if path.is_absolute():
        return path.resolve()

    asset_ctx = coerce_asset_context(assets)
    if asset_ctx is None:
        raise ValidationError(
            f"Mesh path is relative but no asset_root provided: {os.fspath(filename)!r}"
        )

    return asset_ctx.mesh_path(path, ensure_dir=ensure_dir).resolve()
