# The `.artcraft` Bundle Format — Specification v1

> This document is self-contained and language-agnostic. Any agent or program can
> read it and fully support `.artcraft` (produce, read, and verify) without access
> to the Articraft codebase. It can be used directly as a prompt: "Implement support
> for the `.artcraft` format as specified below."

## 1. Purpose

An `.artcraft` file is a **signed, provenance-carrying container** for one
Articraft-generated articulated asset (its URDF, meshes, and compile report). The
embedded Ed25519 signature lets anyone confirm two things with only the file and a
public key:

1. **Authenticity** — the bundle was produced by the holder of a specific private key.
2. **Integrity** — no file inside was altered after signing.

It does not encrypt content; the container is a plain zip and its files are readable
by any zip tool. Security comes from the signature, not from obscurity.

## 2. Container

- The file is a standard **ZIP** archive (DEFLATE is fine). Recommended extension: `.artcraft`.
- **Required entries** (exact names, at the archive root):
  - `manifest.json` — provenance + integrity metadata (see §3).
  - `signature.json` — the detached signature over the manifest (see §5).
- **Payload entries** — every other entry is an asset file stored at its logical path
  (the `arcname`), e.g. `model.urdf`, `compile_report.json`, `assets/meshes/<name>.obj`.
  Payload paths use forward slashes.
- Entries whose basename is `.DS_Store` (or other OS junk) MUST NOT be included.

## 3. `manifest.json`

A single JSON object. Fields:

| Field            | Type                | Meaning |
|------------------|---------------------|---------|
| `format`         | string              | Constant `"artcraft"`. |
| `format_version` | integer             | Constant `1` for this spec. |
| `record_id`      | string \| null      | Source record identifier. |
| `provider`       | string \| null      | Generation provider (e.g. `"openai"`). |
| `model_id`       | string \| null      | Generation model id. |
| `created_at`     | string \| null      | Record creation time (ISO-8601). |
| `lineage`        | object \| null      | Optional origin/parent record references. |
| `exported_at`    | string              | Export time (ISO-8601, UTC recommended). |
| `files`          | array of `{path, sha256}` | One entry per payload file (see below). Sorted ascending by `path`. |

`files[i]`:
- `path` — the payload entry's arcname (exactly as stored in the zip).
- `sha256` — **lowercase hex** SHA-256 of that file's raw bytes.

The `files` array MUST list every payload entry and MUST NOT list `manifest.json` or
`signature.json`.

## 4. Canonical manifest bytes — the signing subject (critical)

The **exact byte sequence of `manifest.json` as stored in the zip** IS the signing
subject. Those bytes MUST be **canonical JSON**:

- UTF-8 encoded.
- Object keys sorted in ascending (code-point) order, recursively.
- Compact separators: `,` between items and `:` between key/value, with **no
  whitespace** (equivalent to Python `json.dumps(obj, sort_keys=True, separators=(",", ":"))`).

Rules:
- A **producer** MUST compute these canonical bytes once, sign those exact bytes, and
  write those exact bytes into the zip as `manifest.json`.
- A **verifier** MUST read `manifest.json`'s raw bytes from the zip and verify the
  signature against them **without** re-parsing and re-serializing. This avoids any
  JSON round-trip mismatch.

## 5. `signature.json`

A single JSON object (its own formatting is irrelevant — it is not signed):

| Field       | Type   | Meaning |
|-------------|--------|---------|
| `algorithm` | string | Constant `"ed25519"`. |
| `public_key`| string | **base64** of the 32-byte raw Ed25519 public key. |
| `signature` | string | **base64** of the 64-byte Ed25519 signature over the canonical manifest bytes (§4). |

## 6. Encodings (summary)

- **Hashes**: SHA-256, lowercase hex.
- **base64**: standard alphabet, with padding.
- **Ed25519 keys/signatures**: raw bytes (public = 32, signature = 64), then base64.

## 7. Verification algorithm

Input: bundle bytes; optionally a trusted `own_public_key` (base64) to decide `is_own`.

1. Open as zip. If `manifest.json` or `signature.json` is missing → **invalid**.
2. Read raw bytes `M` = `manifest.json`; parse `signature.json`.
3. `pub` = base64-decode `signature.public_key`; `sig` = base64-decode `signature.signature`.
4. Ed25519-verify `sig` over `M` with `pub`. If it fails → `signature_valid = false` → **invalid** (stop).
5. Parse `M` as JSON to get `files`. For each `{path, sha256}`: read that entry's bytes
   from the zip and check lowercase-hex SHA-256 equals `sha256`. All match → `files_intact = true`.
6. `valid = signature_valid AND files_intact`.
7. `is_own = (own_public_key is provided AND equals signature.public_key)`.

**Verdict semantics** for a UI/consumer:
- `valid && is_own` → "produced by *this* project's key, untampered".
- `valid && !is_own` → "signature valid and untampered, but signed by a different key
  (another deployment/instance)".
- `!valid` → reject; report whether the signature or a file hash failed.

## 8. Production algorithm

1. Gather payload files as `{arcname: bytes}` (exclude `manifest.json`, `signature.json`, OS junk).
2. Build the manifest object; set `files` = sorted `[{path, sha256_hex(bytes)}]`.
3. Compute canonical bytes `M` (§4).
4. `sig` = Ed25519-sign(`M`) with the private key.
5. Build `signature.json` with `algorithm`, base64 `public_key`, base64 `sig`.
6. Write a zip containing: `manifest.json` = `M` (the exact canonical bytes), `signature.json`,
   then every payload entry at its arcname.

## 9. Key model

- The signer holds an Ed25519 **private key** (32-byte seed). The matching **public key**
  is embedded in every bundle and may be published for third-party verification.
- "Is this from project X?" is answered by comparing the bundle's `public_key` against
  X's known public key (or verifying against it). Multiple instances can share one key
  to be mutually verifiable, or use distinct keys to be attributable per instance.
- Reference deployment (Articraft viewer): private key comes from the
  `ARTICRAFT_SIGNING_PRIVATE_KEY` env var (base64 seed) if set, else a per-instance key
  auto-generated at `<data-root>/keys/signing_ed25519.key`. Its public key is served at
  `GET /api/signing/public-key`.

## 10. Minimal example

`manifest.json` (shown pretty; **stored canonically/minified**):
```json
{"created_at":null,"exported_at":"2026-07-08T00:00:00+00:00","files":[{"path":"model.urdf","sha256":"b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"}],"format":"artcraft","format_version":1,"lineage":null,"model_id":"gpt-5.5","provider":"openai","record_id":"rec_x"}
```
`signature.json`:
```json
{ "algorithm": "ed25519", "public_key": "<base64 32B>", "signature": "<base64 64B>" }
```

## 11. Reference implementation (Python, `cryptography`)

```python
import base64, hashlib, io, json, zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey)

def _canonical(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")

def pack(manifest: dict, files: dict[str, bytes], private_key: Ed25519PrivateKey) -> bytes:
    m = _canonical(manifest)
    sig = {
        "algorithm": "ed25519",
        "public_key": base64.b64encode(private_key.public_key().public_bytes_raw()).decode(),
        "signature": base64.b64encode(private_key.sign(m)).decode(),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", m)
        z.writestr("signature.json", json.dumps(sig, indent=2).encode())
        for name in sorted(files):
            z.writestr(name, files[name])
    return buf.getvalue()

def verify(data: bytes, own_public_key_b64: str | None = None) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        m = z.read("manifest.json")
        sig = json.loads(z.read("signature.json"))
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(sig["public_key"]))
        try:
            pub.verify(base64.b64decode(sig["signature"]), m)
            signature_valid = True
        except Exception:
            return {"valid": False, "signature_valid": False, "reason": "bad signature"}
        manifest = json.loads(m)
        intact = all(
            hashlib.sha256(z.read(f["path"])).hexdigest() == f["sha256"]
            for f in manifest["files"]
        )
        return {
            "valid": intact,
            "signature_valid": True,
            "files_intact": intact,
            "is_own": own_public_key_b64 == sig["public_key"],
            "manifest": manifest,
        }
```

## 12. Versioning

`format_version` is `1`. A future revision that changes the manifest schema, the
canonicalization rules, or the signature algorithm MUST bump `format_version`. A
verifier SHOULD reject a `format_version` it does not understand.
