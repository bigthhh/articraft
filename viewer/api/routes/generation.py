from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request

from viewer.api.generation import (
    GenerationBusyError,
    GenerationLogResponse,
    GenerationManager,
    GenerationOptionsResponse,
    GenerationRequest,
    GenerationSummary,
    GenerationTaskStatus,
    list_provider_options,
)

router = APIRouter()


def _manager(request: Request) -> GenerationManager:
    return request.app.state.generation_manager


@router.get("/api/generation/providers", response_model=GenerationOptionsResponse)
async def generation_providers(request: Request) -> GenerationOptionsResponse:
    return await asyncio.to_thread(list_provider_options, request.app.state.repo_root)


@router.post("/api/generate", response_model=GenerationTaskStatus)
async def create_generation(request: Request, body: GenerationRequest) -> GenerationTaskStatus:
    options = await asyncio.to_thread(list_provider_options, request.app.state.repo_root)
    provider = next((p for p in options.providers if p.value == body.provider), None)
    if provider is None:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")
    if not provider.available:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{body.provider}' has no API key configured.",
        )
    try:
        return await _manager(request).start(body)
    except GenerationBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/generate/status", response_model=GenerationSummary)
async def generation_status(request: Request) -> GenerationSummary:
    return _manager(request).summary()


@router.get("/api/generate/log", response_model=GenerationLogResponse)
async def generation_log(
    request: Request,
    run_id: str | None = Query(default=None),
    tail: int = Query(default=24000, ge=1000, le=200000),
) -> GenerationLogResponse:
    return await asyncio.to_thread(_manager(request).log, run_id, tail)
