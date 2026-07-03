import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.monster import MonsterOut
from app.services import open5e as open5e_service

router = APIRouter()


@router.get("/search")
async def search(q: str):
    try:
        return await open5e_service.search_open5e(q)
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
