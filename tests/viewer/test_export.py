from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from articraft.config import DEFAULT_VIEWER_PASSWORD, DEFAULT_VIEWER_USERNAME
from storage.repo import StorageRepo
from viewer.api import packaging
from viewer.api.app import create_app


def _auth() -> dict[str, str]:
    token = base64.b64encode(
        f"{DEFAULT_VIEWER_USERNAME}:{DEFAULT_VIEWER_PASSWORD}".encode()
    ).decode()
    return {"Authorization": f"Basic {token}"}


def _client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Ed25519PrivateKey]:
    key = Ed25519PrivateKey.generate()
    monkeypatch.setenv(
        packaging.SIGNING_KEY_ENV_VAR,
        base64.b64encode(key.private_bytes_raw()).decode(),
    )
    repo = StorageRepo(tmp_path)
    repo.ensure_layout()
    return TestClient(create_app(repo_root=tmp_path), headers=_auth()), key


def _own_bundle(key: Ed25519PrivateKey) -> bytes:
    files = {"model.urdf": b"<robot/>", "assets/meshes/a.obj": b"v 0 0 0\n"}
    manifest = packaging.build_manifest(
        record_meta={"record_id": "rec_x", "provider": "openai"},
        files=files,
        exported_at="2026-07-08T00:00:00Z",
    )
    return packaging.pack_artc(manifest=manifest, files=files, key=key)


def test_public_key_endpoint(tmp_path: Path, monkeypatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    response = client.get("/api/signing/public-key")
    assert response.status_code == 200
    assert response.json() == {"algorithm": "ed25519", "public_key": packaging.public_key_b64(key)}


def test_verify_accepts_own_bundle(tmp_path: Path, monkeypatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    response = client.post("/api/verify", content=_own_bundle(key))
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True and body["is_own"] is True
    assert body["manifest"]["record_id"] == "rec_x"


def test_verify_rejects_garbage(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client(tmp_path, monkeypatch)
    response = client.post("/api/verify", content=b"not a zip at all")
    assert response.status_code == 200
    assert response.json()["valid"] is False
