from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from storage.repo import StorageRepo
from storage.trajectories import (
    COMPRESSED_TRAJECTORY_FILENAME,
    LEGACY_CONVERSATION_FILENAME,
    SYSTEM_PROMPT_FILENAMES,
    TRAJECTORY_FILENAME,
    compress_trajectory_file,
    ensure_shared_system_prompt_file,
)


@dataclass(slots=True)
class MigrationSummary:
    records_scanned: int = 0
    trajectories_compressed: int = 0
    provenance_updated: int = 0
    shared_prompts_ensured: int = 0
    prompt_files_deleted: int = 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="migrate_record_trajectories.py")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root containing data/records.",
    )
    return parser


def _local_prompt_candidates(trace_dir: Path, expected_name: str | None) -> list[Path]:
    candidates: list[Path] = []
    if expected_name:
        candidate = trace_dir / Path(expected_name).name
        if candidate.exists() and candidate.is_file():
            candidates.append(candidate)
    for path in sorted(trace_dir.iterdir()):
        if not path.is_file() or path in candidates:
            continue
        if path.name in SYSTEM_PROMPT_FILENAMES:
            candidates.append(path)
    return candidates


def _migrate_record(repo: StorageRepo, record_id: str, summary: MigrationSummary) -> None:
    trace_dir = repo.layout.record_traces_dir(record_id)
    if not trace_dir.exists() or not trace_dir.is_dir():
        return

    summary.records_scanned += 1

    compressed_path = trace_dir / COMPRESSED_TRAJECTORY_FILENAME
    plain_trajectory_path = trace_dir / TRAJECTORY_FILENAME
    legacy_trajectory_path = trace_dir / LEGACY_CONVERSATION_FILENAME
    source_path: Path | None = None
    if plain_trajectory_path.exists():
        source_path = plain_trajectory_path
    elif legacy_trajectory_path.exists():
        source_path = legacy_trajectory_path

    if source_path is not None and not compressed_path.exists():
        compress_trajectory_file(source_path, compressed_path)
        summary.trajectories_compressed += 1

    for candidate in (plain_trajectory_path, legacy_trajectory_path):
        if candidate.exists():
            candidate.unlink()

    provenance_path = repo.layout.record_dir(record_id) / "provenance.json"
    provenance = repo.read_json(provenance_path)
    prompting = provenance.get("prompting") if isinstance(provenance, dict) else None
    if isinstance(provenance, dict) and not isinstance(prompting, dict):
        prompting = {}
        provenance["prompting"] = prompting
    prompt_sha = (
        str(prompting.get("system_prompt_sha256"))
        if isinstance(prompting, dict) and prompting.get("system_prompt_sha256")
        else None
    )
    prompt_name = (
        str(prompting.get("system_prompt_file"))
        if isinstance(prompting, dict) and prompting.get("system_prompt_file")
        else None
    )

    prompt_candidates = _local_prompt_candidates(trace_dir, prompt_name)
    if prompt_candidates:
        shared_path = ensure_shared_system_prompt_file(
            repo,
            prompt_candidates[0],
            prompt_sha256=prompt_sha,
        )
        summary.shared_prompts_ensured += 1
        if isinstance(prompting, dict):
            updated = False
            if prompting.get("system_prompt_sha256") != shared_path.stem:
                prompting["system_prompt_sha256"] = shared_path.stem
                updated = True
            if not prompting.get("system_prompt_file"):
                prompting["system_prompt_file"] = prompt_candidates[0].name
                updated = True
            if updated:
                repo.write_json(provenance_path, provenance)
                summary.provenance_updated += 1
        for path in prompt_candidates:
            path.unlink()
            summary.prompt_files_deleted += 1


def migrate_repo(repo_root: Path) -> MigrationSummary:
    repo = StorageRepo(repo_root.resolve())
    repo.ensure_layout()
    summary = MigrationSummary()
    records_root = repo.layout.records_root
    if not records_root.exists():
        return summary

    for record_dir in sorted(path for path in records_root.iterdir() if path.is_dir()):
        _migrate_record(repo, record_dir.name, summary)
    return summary


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    summary = migrate_repo(args.repo_root)
    print(f"records_scanned={summary.records_scanned}")
    print(f"trajectories_compressed={summary.trajectories_compressed}")
    print(f"provenance_updated={summary.provenance_updated}")
    print(f"shared_prompts_ensured={summary.shared_prompts_ensured}")
    print(f"prompt_files_deleted={summary.prompt_files_deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
