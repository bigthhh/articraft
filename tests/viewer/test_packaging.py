from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from viewer.api import packaging


def _bundle() -> tuple[bytes, str]:
    key = Ed25519PrivateKey.generate()
    files = {"model.urdf": b"<robot/>", "assets/meshes/a.obj": b"v 0 0 0\n"}
    manifest = packaging.build_manifest(
        record_meta={"record_id": "rec_x", "provider": "openai", "model_id": "m"},
        files=files,
        exported_at="2026-07-08T00:00:00Z",
    )
    return packaging.pack_artcraft(manifest=manifest, files=files, key=key), packaging.public_key_b64(key)


def _rewrite_entry(data: bytes, name: str, content: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(buffer, "w") as dst:
        for item in src.namelist():
            dst.writestr(item, content if item == name else src.read(item))
    return buffer.getvalue()


def test_roundtrip_verifies_as_own() -> None:
    bundle, pub = _bundle()
    report = packaging.verify_artcraft(bundle, own_public_key_b64=pub)
    assert report["valid"] and report["signature_valid"] and report["files_intact"]
    assert report["is_own"] is True
    assert report["manifest"]["record_id"] == "rec_x"


def test_tampered_payload_fails_integrity() -> None:
    bundle, pub = _bundle()
    tampered = _rewrite_entry(bundle, "model.urdf", b"<robot tampered/>")
    report = packaging.verify_artcraft(tampered, own_public_key_b64=pub)
    assert report["signature_valid"] is True  # manifest untouched
    assert report["files_intact"] is False and report["valid"] is False


def test_tampered_manifest_fails_signature() -> None:
    bundle, _ = _bundle()
    forged = json.dumps({"record_id": "rec_forged", "files": []}).encode()
    tampered = _rewrite_entry(bundle, packaging.MANIFEST_NAME, forged)
    report = packaging.verify_artcraft(tampered)
    assert report["signature_valid"] is False and report["valid"] is False


def test_foreign_key_verifies_but_not_own() -> None:
    bundle, _ = _bundle()
    other_pub = packaging.public_key_b64(Ed25519PrivateKey.generate())
    report = packaging.verify_artcraft(bundle, own_public_key_b64=other_pub)
    assert report["signature_valid"] is True and report["valid"] is True
    assert report["is_own"] is False


def test_key_is_persisted_and_reused(tmp_path: Path) -> None:
    first = packaging.public_key_b64(packaging.load_signing_key(tmp_path))
    assert (tmp_path / "keys" / "signing_ed25519.key").exists()
    second = packaging.public_key_b64(packaging.load_signing_key(tmp_path))
    assert first == second  # reused, not regenerated
