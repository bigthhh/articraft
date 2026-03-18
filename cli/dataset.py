from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cli.common import add_data_root_argument
from storage.categories import CategoryStore
from storage.collections import CollectionStore
from storage.datasets import DatasetStore
from storage.queries import StorageQueries
from storage.records import RecordStore
from storage.repo import StorageRepo
from storage.search import SearchIndex


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True, frozen=True)
class DeleteCategoryPreview:
    category_slug: str
    category_title: str
    record_ids: list[str]
    cached_run_ids: list[str]


@dataclass(slots=True, frozen=True)
class DeleteRecordPreview:
    record_id: str
    record_dir: Path
    title: str
    category_slug: str
    run_id: str
    dataset_id: str
    in_workbench: bool


def _build_delete_category_preview(
    repo: StorageRepo, queries: StorageQueries, category_slug: str
) -> DeleteCategoryPreview | None:
    category = CategoryStore(repo).load(category_slug)
    if not isinstance(category, dict):
        return None
    return DeleteCategoryPreview(
        category_slug=category_slug,
        category_title=str(category.get("title") or ""),
        record_ids=queries.list_record_ids_for_category(category_slug),
        cached_run_ids=queries.list_run_ids_for_category(category_slug),
    )


def _print_delete_category_preview(preview: DeleteCategoryPreview) -> None:
    print("Delete category preview")
    print(f"category_slug={preview.category_slug}")
    print(f"category_title={preview.category_title or '(untitled)'}")
    print(f"category_dir={preview.category_slug}")
    print(f"records_to_delete={len(preview.record_ids)}")
    if preview.record_ids:
        print(f"sample_record_ids={', '.join(preview.record_ids[:5])}")
    else:
        print("sample_record_ids=(none)")
    print(f"run_cache_entries_retained={len(preview.cached_run_ids)}")
    if preview.cached_run_ids:
        print(f"sample_run_ids={', '.join(preview.cached_run_ids[:5])}")


def _resolve_record_path(repo: StorageRepo, record_path: str) -> Path:
    resolved = Path(record_path).expanduser().resolve()
    records_root = repo.layout.records_root.resolve()
    try:
        relative = resolved.relative_to(records_root)
    except ValueError as exc:
        raise ValueError(f"Record path must be inside {records_root}") from exc
    if len(relative.parts) != 1:
        raise ValueError(f"Record path must point to a direct child of {records_root}")
    if not resolved.is_dir():
        raise ValueError(f"Record directory not found: {resolved}")
    return resolved


def _build_delete_record_preview(
    repo: StorageRepo,
    *,
    record_id: str | None,
    record_path: str | None,
) -> DeleteRecordPreview:
    if bool(record_id) == bool(record_path):
        raise ValueError("Provide exactly one of --record-id or --record-path")

    if record_path:
        record_dir = _resolve_record_path(repo, record_path)
        resolved_record_id = record_dir.name
    else:
        resolved_record_id = str(record_id)
        record_dir = repo.layout.record_dir(resolved_record_id).resolve()
        if not record_dir.is_dir():
            raise ValueError(f"Record not found: {resolved_record_id}")

    record = repo.read_json(repo.layout.record_metadata_path(resolved_record_id))
    if not isinstance(record, dict):
        raise ValueError(f"Missing record.json for {resolved_record_id}")

    display = record.get("display") if isinstance(record.get("display"), dict) else {}
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    dataset_entry = (
        repo.read_json(repo.layout.record_dataset_entry_path(resolved_record_id), default={}) or {}
    )
    workbench = CollectionStore(repo).load_workbench() or {}
    entries = workbench.get("entries", []) if isinstance(workbench, dict) else []
    in_workbench = any(
        str(entry.get("record_id") or "") == resolved_record_id
        for entry in entries
        if isinstance(entry, dict)
    )

    return DeleteRecordPreview(
        record_id=resolved_record_id,
        record_dir=record_dir,
        title=str(display.get("title") or ""),
        category_slug=str(record.get("category_slug") or ""),
        run_id=str(source.get("run_id") or ""),
        dataset_id=str(dataset_entry.get("dataset_id") or ""),
        in_workbench=in_workbench,
    )


def _print_delete_record_preview(preview: DeleteRecordPreview) -> None:
    print("Delete record preview")
    print(f"record_id={preview.record_id}")
    print(f"record_dir={preview.record_dir}")
    print(f"title={preview.title or '(untitled)'}")
    print(f"category_slug={preview.category_slug or '(none)'}")
    print(f"run_id={preview.run_id or '(none)'}")
    print(f"dataset_id={preview.dataset_id or '(none)'}")
    print(f"in_workbench={'yes' if preview.in_workbench else 'no'}")


def _delete_category(
    repo: StorageRepo, datasets: DatasetStore, preview: DeleteCategoryPreview
) -> tuple[dict, object]:
    categories = CategoryStore(repo)
    collections = CollectionStore(repo)
    records = RecordStore(repo)

    for record_id in preview.record_ids:
        record = records.load_record(record_id)
        source = record.get("source") if isinstance(record, dict) else None
        run_id = source.get("run_id") if isinstance(source, dict) else None

        collections.remove_workbench_entries(record_id)

        if isinstance(run_id, str) and run_id:
            for path in (
                repo.layout.run_staging_dir(run_id) / record_id,
                repo.layout.run_failures_dir(run_id) / record_id,
            ):
                if path.exists():
                    shutil.rmtree(path)

        records.delete_record(record_id)

    categories.delete(preview.category_slug)
    manifest = datasets.write_dataset_manifest()
    search_stats = SearchIndex(repo).rebuild()
    return manifest, search_stats


def _delete_record(
    repo: StorageRepo, datasets: DatasetStore, preview: DeleteRecordPreview
) -> tuple[dict, object]:
    collections = CollectionStore(repo)
    records = RecordStore(repo)

    collections.remove_workbench_entries(preview.record_id)

    if preview.run_id:
        for path in (
            repo.layout.run_staging_dir(preview.run_id) / preview.record_id,
            repo.layout.run_failures_dir(preview.run_id) / preview.record_id,
        ):
            if path.exists():
                shutil.rmtree(path)

    records.delete_record(preview.record_id)
    manifest = datasets.write_dataset_manifest()
    search_stats = SearchIndex(repo).rebuild()
    return manifest, search_stats


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="articraft-dataset")
    add_data_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-storage", help="Create the canonical data/ directory layout.")
    subparsers.add_parser("status", help="Show dataset storage status.")
    promote = subparsers.add_parser(
        "promote", help="Promote a record into the dataset with a record-local entry."
    )
    promote.add_argument("--record-id", required=True, help="Record identifier to promote.")
    promote.add_argument("--dataset-id", required=True, help="Stable dataset identifier to assign.")
    promote.add_argument(
        "--category-slug", help="Optional category slug override when the record lacks one."
    )
    promote.add_argument(
        "--promoted-at",
        help="UTC timestamp for promotion. Defaults to the current time.",
    )
    delete_category = subparsers.add_parser(
        "delete-category",
        help="Preview or delete an entire category and all records assigned to it.",
    )
    delete_category.add_argument(
        "--category-slug",
        required=True,
        help="Category slug to preview or delete.",
    )
    delete_category.add_argument(
        "--execute",
        action="store_true",
        help="Execute the deletion after the preview checks pass.",
    )
    delete_category.add_argument(
        "--confirm-slug",
        help="Exact category slug confirmation required when --execute is set.",
    )
    delete_record = subparsers.add_parser(
        "delete-record",
        help="Preview or delete a single record by ID or canonical record directory path.",
    )
    delete_record_target = delete_record.add_mutually_exclusive_group(required=True)
    delete_record_target.add_argument(
        "--record-id",
        help="Record identifier to preview or delete.",
    )
    delete_record_target.add_argument(
        "--record-path",
        help="Canonical record directory path under data/records/.",
    )
    delete_record.add_argument(
        "--execute",
        action="store_true",
        help="Execute the deletion after the preview checks pass.",
    )
    delete_record.add_argument(
        "--confirm-record-id",
        help="Exact record ID confirmation required when --execute is set.",
    )
    subparsers.add_parser("validate", help="Validate record-local dataset entries.")
    subparsers.add_parser(
        "build-manifest", help="Build the derived dataset manifest under data/cache/manifests/."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo = StorageRepo(args.repo_root)
    datasets = DatasetStore(repo)
    queries = StorageQueries(repo)

    if args.command == "init-storage":
        repo.ensure_layout()
        print(f"Initialized dataset storage at {repo.layout.data_root}")
        return 0

    if args.command == "status":
        record_count = len(queries.list_record_ids())
        category_count = len(queries.list_category_slugs())
        dataset_entries = datasets.list_entries()
        print(
            f"records={record_count} categories={category_count} dataset_entries={len(dataset_entries)}"
        )
        return 0

    if args.command == "promote":
        repo.ensure_layout()
        try:
            entry = datasets.promote_record(
                record_id=args.record_id,
                dataset_id=args.dataset_id,
                category_slug=args.category_slug,
                promoted_at=args.promoted_at or _utc_now(),
            )
        except ValueError as exc:
            print(str(exc))
            return 1
        print(
            "Promoted "
            f"record_id={entry['record_id']} dataset_id={entry['dataset_id']} "
            f"at {repo.layout.record_dataset_entry_path(entry['record_id'])}"
        )
        return 0

    if args.command == "delete-category":
        repo.ensure_layout()
        preview = _build_delete_category_preview(repo, queries, args.category_slug)
        if preview is None:
            print(f"Category not found: {args.category_slug}")
            return 1

        _print_delete_category_preview(preview)
        if not args.execute:
            print(
                "Preview only. Re-run with "
                f"--execute --confirm-slug {preview.category_slug} "
                "to permanently delete this category."
            )
            return 0

        if args.confirm_slug != preview.category_slug:
            print(
                "Refusing to delete category: "
                f"--confirm-slug must exactly match {preview.category_slug}"
            )
            return 1

        manifest, search_stats = _delete_category(repo, datasets, preview)
        print(
            f"Deleted category_slug={preview.category_slug} "
            f"records_deleted={len(preview.record_ids)} "
            f"run_cache_entries_retained={len(preview.cached_run_ids)}"
        )
        print(
            f"Wrote dataset manifest to {repo.layout.dataset_manifest_path()} "
            f"entries={len(manifest['generated'])}"
        )
        print(
            f"Rebuilt search index at {search_stats.path} "
            f"records={search_stats.record_count} "
            f"categories={search_stats.category_count}"
        )
        return 0

    if args.command == "delete-record":
        repo.ensure_layout()
        try:
            preview = _build_delete_record_preview(
                repo,
                record_id=args.record_id,
                record_path=args.record_path,
            )
        except ValueError as exc:
            print(str(exc))
            return 1

        _print_delete_record_preview(preview)
        if not args.execute:
            print(
                "Preview only. Re-run with "
                f"--execute --confirm-record-id {preview.record_id} "
                "to permanently delete this record."
            )
            return 0

        if args.confirm_record_id != preview.record_id:
            print(
                "Refusing to delete record: "
                f"--confirm-record-id must exactly match {preview.record_id}"
            )
            return 1

        manifest, search_stats = _delete_record(repo, datasets, preview)
        print(
            f"Deleted record_id={preview.record_id} "
            f"category_slug={preview.category_slug or '(none)'} "
            f"run_id_retained={preview.run_id or '(none)'}"
        )
        print(
            f"Wrote dataset manifest to {repo.layout.dataset_manifest_path()} "
            f"entries={len(manifest['generated'])}"
        )
        print(
            f"Rebuilt search index at {search_stats.path} "
            f"records={search_stats.record_count} "
            f"categories={search_stats.category_count}"
        )
        return 0

    if args.command == "validate":
        errors = datasets.validate()
        if errors:
            for error in errors:
                print(error)
            return 1
        print(f"Dataset valid: entries={len(datasets.list_entries())}")
        return 0

    if args.command == "build-manifest":
        repo.ensure_layout()
        manifest = datasets.write_dataset_manifest()
        print(
            f"Wrote dataset manifest to {repo.layout.dataset_manifest_path()} entries={len(manifest['generated'])}"
        )
        return 0

    parser.error(f"Unhandled command: {args.command}")
    return 2
