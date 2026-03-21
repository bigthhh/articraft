from __future__ import annotations

import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from storage.repo import StorageRepo
from storage.trajectories import COMPRESSED_TRAJECTORY_FILENAME, unroll_record_trajectory


def _parse_concurrency(raw_value: str) -> int:
    if raw_value == "auto":
        return max(1, os.cpu_count() or 1)
    value = int(raw_value)
    if value <= 0:
        raise ValueError("concurrency must be positive")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="unroll_all_trajectories.py")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root containing data/records.",
    )
    parser.add_argument(
        "--concurrency",
        default="auto",
        help="Worker count or 'auto'.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of records to process.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate unrolled cache files even if they are already up to date.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    repo = StorageRepo(args.repo_root.resolve())
    repo.ensure_layout()
    record_dirs = sorted(path for path in repo.layout.records_root.iterdir() if path.is_dir())
    record_ids = [
        record_dir.name
        for record_dir in record_dirs
        if (
            repo.layout.record_traces_dir(record_dir.name) / COMPRESSED_TRAJECTORY_FILENAME
        ).exists()
    ]
    if args.limit is not None:
        record_ids = record_ids[: args.limit]

    concurrency = _parse_concurrency(str(args.concurrency))
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        targets = list(
            executor.map(
                lambda record_id: unroll_record_trajectory(repo, record_id, force=args.force),
                record_ids,
            )
        )

    print(f"unrolled={len(targets)}")
    for target in targets:
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
