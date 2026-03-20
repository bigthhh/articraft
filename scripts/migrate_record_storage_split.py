from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from storage.repo import StorageRepo

RECORD_SCHEMA_VERSION = 2
PROVENANCE_SCHEMA_VERSION = 2


@dataclass(slots=True)
class MigrationSummary:
    record_json_updated: int = 0
    provenance_updated: int = 0
    compile_reports_deleted: int = 0
    urdfs_deleted: int = 0
    assets_deleted: int = 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="migrate_record_storage_split.py")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root containing data/records.",
    )
    return parser


def _normalize_record_payload(record: dict) -> dict:
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
    normalized_artifacts = {
        "prompt_txt": str(artifacts.get("prompt_txt") or "prompt.txt"),
        "prompt_series_json": artifacts.get("prompt_series_json"),
        "model_py": str(artifacts.get("model_py") or "model.py"),
        "provenance_json": str(artifacts.get("provenance_json") or "provenance.json"),
        "cost_json": artifacts.get("cost_json"),
        "inputs_dir": str(artifacts.get("inputs_dir") or "inputs"),
    }

    hashes = record.get("hashes")
    if not isinstance(hashes, dict):
        hashes = {}
    normalized_hashes = {
        "prompt_sha256": hashes.get("prompt_sha256"),
        "model_py_sha256": hashes.get("model_py_sha256"),
    }

    record["schema_version"] = RECORD_SCHEMA_VERSION
    record["artifacts"] = normalized_artifacts
    record["hashes"] = normalized_hashes
    record.pop("derived_assets", None)
    return record


def _normalize_provenance_payload(provenance: dict) -> dict:
    provenance["schema_version"] = PROVENANCE_SCHEMA_VERSION
    provenance.pop("materialization", None)
    return provenance


def migrate_repo(repo_root: Path) -> MigrationSummary:
    repo = StorageRepo(repo_root)
    summary = MigrationSummary()

    for record_dir in sorted(path for path in repo.layout.records_root.iterdir() if path.is_dir()):
        record_path = repo.layout.record_metadata_path(record_dir.name)
        record = repo.read_json(record_path)
        if isinstance(record, dict):
            repo.write_json(record_path, _normalize_record_payload(record))
            summary.record_json_updated += 1

        provenance_path = record_dir / "provenance.json"
        provenance = repo.read_json(provenance_path)
        if isinstance(provenance, dict):
            repo.write_json(provenance_path, _normalize_provenance_payload(provenance))
            summary.provenance_updated += 1

        compile_report_path = record_dir / "compile_report.json"
        if compile_report_path.exists():
            compile_report_path.unlink()
            summary.compile_reports_deleted += 1

        urdf_path = record_dir / "model.urdf"
        if urdf_path.exists():
            urdf_path.unlink()
            summary.urdfs_deleted += 1

        assets_dir = record_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
            summary.assets_deleted += 1

    return summary


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    summary = migrate_repo(args.repo_root.resolve())
    print(f"record_json_updated={summary.record_json_updated}")
    print(f"provenance_updated={summary.provenance_updated}")
    print(f"compile_reports_deleted={summary.compile_reports_deleted}")
    print(f"urdfs_deleted={summary.urdfs_deleted}")
    print(f"assets_deleted={summary.assets_deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
