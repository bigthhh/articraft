from __future__ import annotations

import queue
from pathlib import Path
from types import SimpleNamespace

from cli import compile_all


def test_compile_all_worker_uses_materialization_component(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeViewerStore:
        def __init__(self, repo_root: Path, *, ensure_search_index: bool = True) -> None:
            self.repo_root = repo_root
            self.ensure_search_index = ensure_search_index
            self.materialization = self

        def materialize_record_assets(self, record_id: str, **kwargs: object) -> object:
            calls.append((record_id, dict(kwargs)))
            return SimpleNamespace(compiled=True)

    import viewer.api.store as store_module

    monkeypatch.setattr(store_module, "ViewerStore", FakeViewerStore)

    task_queue: queue.Queue[object] = queue.Queue()
    result_queue: queue.Queue[object] = queue.Queue()
    candidate = compile_all.CompileCandidate(record_id="rec_demo", reason="forced", force=True)
    task_queue.put(candidate)
    task_queue.put(None)

    compile_all._worker_loop(
        7,
        1,
        str(tmp_path),
        False,
        "visual",
        task_queue,
        result_queue,
    )

    assert calls == [
        (
            "rec_demo",
            {
                "force": True,
                "ignore_geom_qc": True,
                "validate": False,
                "target": "visual",
                "use_compile_timeout": False,
            },
        )
    ]
    assert result_queue.get_nowait().event == "started"
    finished = result_queue.get_nowait()
    assert finished.event == "finished"
    assert finished.record_id == "rec_demo"
    assert finished.compiled is True
