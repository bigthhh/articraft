from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


from storage.layout import StorageLayout


def main() -> None:
    layout = StorageLayout(Path("/tmp/articraft"))
    assert layout.record_dir("rec_123") == Path("/tmp/articraft/data/records/rec_123")
    assert layout.record_dataset_entry_path("rec_123") == Path(
        "/tmp/articraft/data/records/rec_123/dataset_entry.json"
    )
    assert layout.record_traces_dir("rec_123") == Path("/tmp/articraft/data/records/rec_123/traces")
    assert layout.record_assets_dir("rec_123") == Path("/tmp/articraft/data/records/rec_123/assets")
    assert layout.record_asset_meshes_dir("rec_123") == Path(
        "/tmp/articraft/data/records/rec_123/assets/meshes"
    )
    assert layout.record_asset_glb_dir("rec_123") == Path(
        "/tmp/articraft/data/records/rec_123/assets/glb"
    )
    assert layout.record_asset_viewer_dir("rec_123") == Path(
        "/tmp/articraft/data/records/rec_123/assets/viewer"
    )
    assert layout.local_workbench_path() == Path("/tmp/articraft/data/local/workbench.json")
    assert layout.dataset_manifest_path() == Path(
        "/tmp/articraft/data/cache/manifests/dataset.json"
    )
    assert layout.run_dir("run_123") == Path("/tmp/articraft/data/cache/runs/run_123")


if __name__ == "__main__":
    main()
