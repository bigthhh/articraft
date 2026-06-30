from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storage.library_manifest import rebuild_manifest
from storage.repo import StorageRepo
from viewer.api.app import create_app


def _client(tmp_path: Path) -> TestClient:
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()
    rebuild_manifest(repo)
    return TestClient(create_app(repo_root=tmp_path))


def test_protected_endpoint_requires_credentials(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/api/bootstrap")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].lower().startswith("basic")


def test_default_credentials_grant_access(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/api/bootstrap", auth=("admin", "wanaka@123"))
    assert response.status_code == 200


def test_wrong_credentials_are_rejected(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/api/bootstrap", auth=("admin", "nope"))
    assert response.status_code == 401


def test_health_endpoint_is_public(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/health")
    assert response.status_code == 200


def test_credentials_are_configurable_via_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARTICRAFT_VIEWER_USERNAME", "operator")
    monkeypatch.setenv("ARTICRAFT_VIEWER_PASSWORD", "s3cret")
    client = _client(tmp_path)

    assert client.get("/api/bootstrap", auth=("operator", "s3cret")).status_code == 200
    assert client.get("/api/bootstrap", auth=("admin", "wanaka@123")).status_code == 401
