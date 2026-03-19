from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

from cli.dataset import main as dataset_main
from storage.categories import CategoryStore
from storage.collections import CollectionStore
from storage.datasets import DatasetStore
from storage.models import (
    CategoryRecord,
    DisplayMetadata,
    Record,
    RecordArtifacts,
    RunRecord,
    SourceRef,
)
from storage.records import RecordStore
from storage.repo import StorageRepo
from storage.runs import RunStore


def test_dataset_cli_commands_cover_promote_delete_and_prune(tmp_path: Path) -> None:
    repo_root = tmp_path
    repo = StorageRepo(repo_root)
    repo.ensure_layout()
    CategoryStore(repo).save(
        CategoryRecord(
            schema_version=1,
            slug="hinges",
            title="Hinges",
        )
    )

    record = Record(
        schema_version=1,
        record_id="rec_cli",
        created_at="2026-03-18T00:00:00Z",
        updated_at="2026-03-18T00:00:00Z",
        rating=None,
        kind="generated_model",
        prompt_kind="single_prompt",
        category_slug="hinges",
        source=SourceRef(run_id="run_cli"),
        sdk_package="sdk",
        provider="openai",
        model_id="gpt-5.4",
        display=DisplayMetadata(title="CLI", prompt_preview="cli prompt"),
        artifacts=RecordArtifacts(
            prompt_txt="prompt.txt",
            prompt_series_json=None,
            model_py="model.py",
            model_urdf="model.urdf",
            compile_report_json="compile_report.json",
            provenance_json="provenance.json",
            cost_json=None,
        ),
        collections=["workbench"],
    )
    RecordStore(repo).write_record(record)
    CollectionStore(repo).append_workbench_entry(
        record_id="rec_cli",
        added_at="2026-03-18T00:00:30Z",
        label="CLI entry",
    )
    RunStore(repo).write_run(
        RunRecord(
            schema_version=1,
            run_id="run_cli",
            run_mode="dataset_single",
            collection="dataset",
            created_at="2026-03-18T00:00:00Z",
            updated_at="2026-03-18T00:00:01Z",
            provider="openai",
            model_id="gpt-5.4",
            sdk_package="sdk",
            status="success",
            category_slug="hinges",
            prompt_count=1,
        )
    )
    repo.layout.search_index_path().write_text("sqlite-placeholder", encoding="utf-8")
    output = io.StringIO()
    with redirect_stdout(output):
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "promote",
                    "--record-id",
                    "rec_cli",
                    "--dataset-id",
                    "cli_dataset_001",
                    "--promoted-at",
                    "2026-03-18T00:01:00Z",
                ]
            )
            == 0
        )
        assert dataset_main(["--repo-root", str(repo_root), "validate"]) == 0
        assert dataset_main(["--repo-root", str(repo_root), "build-manifest"]) == 0
        assert dataset_main(["--repo-root", str(repo_root), "status"]) == 0
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "delete-record",
                    "--record-path",
                    str(repo.layout.record_dir("rec_cli")),
                ]
            )
            == 0
        )
        assert repo.layout.record_metadata_path("rec_cli").exists()
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "delete-record",
                    "--record-path",
                    str(repo.layout.record_dir("rec_cli")),
                    "--execute",
                    "--confirm-record-id",
                    "wrong-record-id",
                ]
            )
            == 1
        )
        assert repo.layout.record_metadata_path("rec_cli").exists()
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "delete-record",
                    "--record-path",
                    str(repo.layout.record_dir("rec_cli")),
                    "--execute",
                    "--confirm-record-id",
                    "rec_cli",
                ]
            )
            == 0
        )
        assert not repo.layout.record_dir("rec_cli").exists()
        assert repo.layout.run_metadata_path("run_cli").exists()
        assert repo.layout.search_index_path().exists()
        assert (CollectionStore(repo).load_workbench() or {}).get("entries", []) == []
        assert DatasetStore(repo).list_entries() == []
        empty_record_stage_dir = repo.layout.run_staging_dir("run_cli") / "rec_empty"
        empty_record_stage_dir.mkdir(parents=True, exist_ok=True)
        empty_nested_failure_dir = repo.layout.run_failures_dir("run_cli") / "rec_empty" / "logs"
        empty_nested_failure_dir.mkdir(parents=True, exist_ok=True)
        nonempty_stage_dir = repo.layout.run_staging_dir("run_cli") / "rec_keep"
        nonempty_stage_dir.mkdir(parents=True, exist_ok=True)
        (nonempty_stage_dir / "artifact.txt").write_text("keep", encoding="utf-8")
        failed_stage_dir = repo.layout.run_staging_dir("run_cli") / "rec_failed"
        failed_stage_dir.mkdir(parents=True, exist_ok=True)
        (failed_stage_dir / "artifact.txt").write_text("failed", encoding="utf-8")
        RunStore(repo).append_result(
            "run_cli",
            {
                "record_id": "rec_failed",
                "status": "failed",
                "staging_dir": "data/cache/runs/run_cli/staging/rec_failed",
            },
        )
        search_index_before_prune = repo.layout.search_index_path().read_bytes()
        assert dataset_main(["--repo-root", str(repo_root), "prune-cache"]) == 0
        assert empty_record_stage_dir.exists()
        assert empty_nested_failure_dir.exists()
        assert nonempty_stage_dir.exists()
        assert failed_stage_dir.exists()
        assert dataset_main(["--repo-root", str(repo_root), "prune-cache", "--execute"]) == 0
        assert not empty_record_stage_dir.exists()
        assert not empty_nested_failure_dir.exists()
        assert nonempty_stage_dir.exists()
        assert not failed_stage_dir.exists()
        assert repo.layout.search_index_path().read_bytes() == search_index_before_prune

    category_output = io.StringIO()
    with redirect_stdout(category_output):
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "delete-category",
                    "--category-slug",
                    "hinges",
                ]
            )
            == 0
        )
        assert repo.layout.category_metadata_path("hinges").exists()
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "delete-category",
                    "--category-slug",
                    "hinges",
                    "--execute",
                    "--confirm-slug",
                    "wrong-slug",
                ]
            )
            == 1
        )
        assert repo.layout.category_metadata_path("hinges").exists()
        assert (
            dataset_main(
                [
                    "--repo-root",
                    str(repo_root),
                    "delete-category",
                    "--category-slug",
                    "hinges",
                    "--execute",
                    "--confirm-slug",
                    "hinges",
                ]
            )
            == 0
        )

    manifest = repo.layout.dataset_manifest_path().read_text(encoding="utf-8")
    assert '"generated": []' in manifest
    assert "dataset_entries=1" in output.getvalue()
    assert "Preview only. Re-run with --execute --confirm-record-id rec_cli" in output.getvalue()
    assert "Refusing to delete record" in output.getvalue()
    assert (
        "Deleted record_id=rec_cli category_slug=hinges run_id_retained=run_cli"
        in output.getvalue()
    )
    assert "failed_staging_dirs_to_remove=1" in output.getvalue()
    assert "empty_dirs_to_remove=4" in output.getvalue()
    assert "Preview only. Re-run with --execute to remove these cache paths." in output.getvalue()
    assert "Removed cache paths: 5" in output.getvalue()
    assert "record_dir=" in output.getvalue()
    assert "in_workbench=yes" in output.getvalue()
    assert "Preview only. Re-run with --execute --confirm-slug hinges" in category_output.getvalue()
    assert "Refusing to delete category" in category_output.getvalue()
    assert (
        "Deleted category_slug=hinges records_deleted=0 run_cache_entries_retained=1"
        in category_output.getvalue()
    )
    assert not repo.layout.category_dir("hinges").exists()
