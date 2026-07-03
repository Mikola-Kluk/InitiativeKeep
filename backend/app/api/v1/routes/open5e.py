import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.monster import MonsterOut
from app.schemas.open5e import (
    BulkImportRequest,
    BulkImportResult,
    Open5eBrowse,
    Open5eSource,
)
from app.services import open5e as open5e_service

router = APIRouter()


@router.get("/monsters", response_model=Open5eBrowse)
async def browse(
    q: str | None = None,
    cr: str | None = None,
    type: str | None = None,
    document: str | None = None,
    page: int = 1,
):
    try:
        return await open5e_service.browse_open5e(
            query=q, cr=cr, type=type, document=document, page=page
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Open5e API error: {exc}")


@router.get("/monsters/{slug}", response_model=MonsterOut)
async def preview(slug: str):
    try:
        monster = await open5e_service.preview_open5e(slug)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Open5e API error: {exc}")
    if not monster:
        raise HTTPException(status_code=404, detail=f"Monster '{slug}' not found on Open5e")
    return monster


@router.get("/sources", response_model=list[Open5eSource])
async def sources():
    try:
        return await open5e_service.list_sources()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Open5e API error: {exc}")


@router.post("/import/{slug}", response_model=MonsterOut, status_code=201)
async def import_monster(slug: str):
    try:
        monster = await open5e_service.import_monster(slug)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Open5e API error: {exc}")
    if not monster:
        raise HTTPException(status_code=404, detail=f"Monster '{slug}' not found on Open5e")
    return monster


@router.post("/import", response_model=BulkImportResult)
async def import_bulk(data: BulkImportRequest):
    return await open5e_service.import_many(data.slugs)
