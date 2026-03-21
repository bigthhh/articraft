from __future__ import annotations

import json
from pathlib import Path

from scripts.migrate_record_trajectories import migrate_repo
from storage.repo import StorageRepo


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_migrate_record_trajectories_compresses_and_deduplicates(tmp_path: Path) -> None:
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()

    shared_prompt_text = "shared system prompt\n"
    for record_id in ("rec_001", "rec_002"):
        trace_dir = repo.layout.record_traces_dir(record_id)
        trace_dir.mkdir(parents=True, exist_ok=True)
        (trace_dir / "conversation.jsonl").write_text(
            '{"type":"message","message":{"role":"assistant","content":"done"}}\n',
            encoding="utf-8",
        )
        (trace_dir / "designer_system_prompt.txt").write_text(
            shared_prompt_text,
            encoding="utf-8",
        )
        _write_json(
            repo.layout.record_dir(record_id) / "provenance.json",
            {
                "schema_version": 2,
                "record_id": record_id,
                "prompting": {
                    "system_prompt_file": "designer_system_prompt.txt",
                },
            },
        )
        _write_json(repo.layout.record_metadata_path(record_id), {"record_id": record_id})

    summary = migrate_repo(tmp_path)

    assert summary.records_scanned == 2
    assert summary.trajectories_compressed == 2
    assert summary.provenance_updated == 2
    assert summary.shared_prompts_ensured == 2
    assert summary.prompt_files_deleted == 2

    prompt_files = list(repo.layout.system_prompts_root.glob("*.txt"))
    assert len(prompt_files) == 1
    assert prompt_files[0].read_text(encoding="utf-8") == shared_prompt_text

    for record_id in ("rec_001", "rec_002"):
        trace_dir = repo.layout.record_traces_dir(record_id)
        assert (trace_dir / "trajectory.jsonl.zst").exists()
        assert not (trace_dir / "conversation.jsonl").exists()
        assert not (trace_dir / "designer_system_prompt.txt").exists()
        provenance = repo.read_json(repo.layout.record_dir(record_id) / "provenance.json")
        assert provenance["prompting"]["system_prompt_sha256"] == prompt_files[0].stem


def test_migrate_record_trajectories_is_idempotent(tmp_path: Path) -> None:
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()
    trace_dir = repo.layout.record_traces_dir("rec_001")
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "conversation.jsonl").write_text(
        '{"type":"message","message":{"role":"assistant","content":"done"}}\n',
        encoding="utf-8",
    )
    (trace_dir / "designer_system_prompt.txt").write_text(
        "prompt text\n",
        encoding="utf-8",
    )
    _write_json(
        repo.layout.record_dir("rec_001") / "provenance.json",
        {
            "schema_version": 2,
            "record_id": "rec_001",
            "prompting": {
                "system_prompt_file": "designer_system_prompt.txt",
            },
        },
    )
    _write_json(repo.layout.record_metadata_path("rec_001"), {"record_id": "rec_001"})

    first = migrate_repo(tmp_path)
    second = migrate_repo(tmp_path)

    assert first.trajectories_compressed == 1
    assert first.provenance_updated == 1
    assert second.records_scanned == 1
    assert second.trajectories_compressed == 0
    assert second.provenance_updated == 0
    assert second.prompt_files_deleted == 0
