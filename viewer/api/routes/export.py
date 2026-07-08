from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from viewer.api.dependencies import ViewerStoreDep
from viewer.api.packaging import (
    build_manifest,
    load_signing_key,
    pack_artc,
    public_key_b64,
    verify_artc,
)

router = APIRouter()

_MAX_BUNDLE_BYTES = 200 * 1024 * 1024


@router.get("/api/records/{record_id}/export.artc")
async def export_record(record_id: str, store: ViewerStoreDep) -> Response:
    record = store.record_store.load_record(record_id)
    if not isinstance(record, dict):
        raise HTTPException(status_code=404, detail=f"Record not found: {record_id}")

    await asyncio.to_thread(store.materialization.materialize_record_assets, record_id)

    materialization_dir = store.repo.layout.record_materialization_dir(record_id)
    files = {
        path.relative_to(materialization_dir).as_posix(): path.read_bytes()
        for path in sorted(materialization_dir.rglob("*"))
        if path.is_file() and path.name != ".DS_Store"
    }
    if not files:
        raise HTTPException(
            status_code=409,
            detail="No materialized assets to export; compile the record first.",
        )

    manifest = build_manifest(
        record_meta=record,
        files=files,
        exported_at=datetime.now(timezone.utc).isoformat(),
    )
    key = load_signing_key(store.repo.layout.data_root)
    bundle = pack_artc(manifest=manifest, files=files, key=key)

    return Response(
        content=bundle,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{record_id}.artc"'},
    )


@router.get("/api/signing/public-key")
async def signing_public_key(store: ViewerStoreDep) -> dict:
    key = load_signing_key(store.repo.layout.data_root)
    return {"algorithm": "ed25519", "public_key": public_key_b64(key)}


@router.post("/api/verify")
async def verify_bundle(request: Request, store: ViewerStoreDep) -> dict:
    data = await request.body()
    if len(data) > _MAX_BUNDLE_BYTES:
        raise HTTPException(status_code=413, detail="Bundle exceeds the size limit.")
    own = public_key_b64(load_signing_key(store.repo.layout.data_root))
    return verify_artc(data, own_public_key_b64=own)
