"""Sign and verify `.artc` export bundles.

An `.artc` file is a plain zip carrying the record's `model.urdf`, meshes and
compile report, plus a `manifest.json` (provenance + per-file sha256) and a
`signature.json` (Ed25519 signature over the manifest bytes). The signature proves
the bundle came from this project's private key and that no file was altered.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

FORMAT = "artc"
FORMAT_VERSION = 1
MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "signature.json"
SIGNING_KEY_ENV_VAR = "ARTICRAFT_SIGNING_PRIVATE_KEY"


def load_signing_key(data_root: Path) -> Ed25519PrivateKey:
    """Env-configured key wins (shared across instances); otherwise load or mint a
    per-instance key under ``<data-root>/keys/`` so signing works with zero config."""
    configured = os.getenv(SIGNING_KEY_ENV_VAR, "").strip()
    if configured:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(configured))

    key_path = data_root / "keys" / "signing_ed25519.key"
    if key_path.exists():
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(key_path.read_bytes()))

    key = Ed25519PrivateKey.generate()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(base64.b64encode(key.private_bytes_raw()))
    os.chmod(key_path, 0o600)
    return key


def public_key_b64(key: Ed25519PrivateKey) -> str:
    return base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")


def _canonical(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_manifest(*, record_meta: dict, files: dict[str, bytes], exported_at: str) -> dict:
    return {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "record_id": record_meta.get("record_id"),
        "provider": record_meta.get("provider"),
        "model_id": record_meta.get("model_id"),
        "created_at": record_meta.get("created_at"),
        "lineage": record_meta.get("lineage"),
        "exported_at": exported_at,
        "files": [
            {"path": name, "sha256": hashlib.sha256(files[name]).hexdigest()}
            for name in sorted(files)
        ],
    }


def pack_artc(*, manifest: dict, files: dict[str, bytes], key: Ed25519PrivateKey) -> bytes:
    """Build a signed `.artc` zip from the manifest and file payloads."""
    manifest_bytes = _canonical(manifest)
    signature = {
        "algorithm": "ed25519",
        "public_key": public_key_b64(key),
        "signature": base64.b64encode(key.sign(manifest_bytes)).decode("ascii"),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_NAME, manifest_bytes)
        archive.writestr(SIGNATURE_NAME, json.dumps(signature, indent=2).encode("utf-8"))
        for name in sorted(files):
            archive.writestr(name, files[name])
    return buffer.getvalue()


def verify_artc(data: bytes, *, own_public_key_b64: str | None = None) -> dict:
    """Verify a bundle's signature and file integrity.

    Returns a report; ``valid`` means signature checks out AND every payload file
    matches its manifest hash. ``is_own`` means it was signed by this instance's key.
    """
    report: dict = {
        "valid": False,
        "signature_valid": False,
        "files_intact": False,
        "is_own": False,
        "manifest": None,
        "public_key": None,
        "reason": None,
    }
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            if MANIFEST_NAME not in names or SIGNATURE_NAME not in names:
                report["reason"] = "missing manifest.json or signature.json"
                return report
            manifest_bytes = archive.read(MANIFEST_NAME)
            signature = json.loads(archive.read(SIGNATURE_NAME))
            manifest = json.loads(manifest_bytes)
            report["manifest"] = manifest

            public_key_value = signature.get("public_key")
            report["public_key"] = public_key_value
            try:
                public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_value))
                public_key.verify(base64.b64decode(signature["signature"]), manifest_bytes)
                report["signature_valid"] = True
            except (InvalidSignature, ValueError, TypeError):
                report["reason"] = "signature does not verify"
                return report

            expected = {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}
            intact = all(
                name in names
                and hashlib.sha256(archive.read(name)).hexdigest() == digest
                for name, digest in expected.items()
            )
            report["files_intact"] = intact
            report["is_own"] = own_public_key_b64 is not None and public_key_value == own_public_key_b64
            report["valid"] = intact
            if not intact:
                report["reason"] = "a payload file does not match its manifest hash"
    except (zipfile.BadZipFile, KeyError, ValueError, json.JSONDecodeError) as exc:
        report["reason"] = f"not a readable artc bundle: {exc}"
    return report
