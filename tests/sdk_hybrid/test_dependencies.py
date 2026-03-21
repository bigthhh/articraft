from __future__ import annotations

import importlib

import pytest

from sdk._dependencies import ensure_sdk_hybrid_dependencies, require_cadquery


def test_require_cadquery_reports_precise_install_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None):
        if name == "cadquery":
            raise ModuleNotFoundError("No module named 'cadquery'")
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match=r"Run `uv sync --group dev`"):
        require_cadquery(feature="`sdk_hybrid`")


def test_ensure_sdk_hybrid_dependencies_requires_cadquery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_require(*, feature: str):
        raise RuntimeError(f"{feature} missing cadquery")

    monkeypatch.setattr("sdk._dependencies.require_cadquery", fail_require)

    with pytest.raises(RuntimeError, match="`sdk_hybrid` missing cadquery"):
        ensure_sdk_hybrid_dependencies()
