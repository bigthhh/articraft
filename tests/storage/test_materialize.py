from __future__ import annotations

import pytest

from storage.materialize import ensure_record_artifacts_exist, infer_materialization_status
from storage.repo import StorageRepo


def test_infer_materialization_status_marks_primitive_only_success_as_available(
    tmp_path,
) -> None:
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()

    record_id = "rec_primitive"
    materialization_dir = repo.layout.record_materialization_dir(record_id)
    materialization_dir.mkdir(parents=True, exist_ok=True)
    (materialization_dir / "model.urdf").write_text(
        "<robot name='primitive'><link name='base'><visual><geometry><box size='1 1 1'/></geometry></visual></link></robot>",
        encoding="utf-8",
    )

    status = infer_materialization_status(repo, record_id)

    assert status == "available"


def test_infer_materialization_status_keeps_mesh_backed_urdf_missing_without_assets(
    tmp_path,
) -> None:
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()

    record_id = "rec_mesh"
    materialization_dir = repo.layout.record_materialization_dir(record_id)
    materialization_dir.mkdir(parents=True, exist_ok=True)
    (materialization_dir / "model.urdf").write_text(
        "<robot name='mesh'><link name='base'><visual><geometry><mesh filename='assets/meshes/base.obj'/></geometry></visual></link></robot>",
        encoding="utf-8",
    )

    status = infer_materialization_status(repo, record_id)

    assert status == "missing"


def test_ensure_record_artifacts_exist_raises_for_missing_canonical_files(tmp_path) -> None:
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()

    record_id = "rec_broken"
    record_dir = repo.layout.record_dir(record_id)
    record_dir.mkdir(parents=True, exist_ok=True)
    (record_dir / "record.json").write_text(
        '{"artifacts":{"model_py":"model.py","provenance_json":"provenance.json"}}',
        encoding="utf-8",
    )
    (record_dir / "provenance.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="missing canonical artifact"):
        ensure_record_artifacts_exist(
            repo,
            record_id,
            required=("model_py", "provenance_json"),
        )
