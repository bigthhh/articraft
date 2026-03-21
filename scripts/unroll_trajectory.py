from __future__ import annotations

import argparse
from pathlib import Path

from storage.repo import StorageRepo
from storage.trajectories import unroll_record_trajectory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="unroll_trajectory.py")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root containing data/records.",
    )
    parser.add_argument("record_dir", type=Path, help="Canonical record directory path.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate the unrolled cache even if it is already up to date.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    repo = StorageRepo(args.repo_root.resolve())
    repo.ensure_layout()
    record_id = args.record_dir.resolve().name
    target = unroll_record_trajectory(repo, record_id, force=args.force)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
