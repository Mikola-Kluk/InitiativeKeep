from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from app.schemas.monster import MonsterCreate, MonsterOut, MonsterUpdate
from app.services import monster as monster_service

router = APIRouter()


@router.get("/", response_model=list[MonsterOut])
async def list_monsters(search: str | None = None):
    return await monster_service.get_all_monsters(search)


@router.get("/{monster_id}", response_model=MonsterOut)
async def get_monster(monster_id: int):
    monster = await monster_service.get_monster(monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")
    return monster


@router.post("/", response_model=MonsterOut, status_code=201)
async def create_monster(data: MonsterCreate):
    return await monster_service.create_monster(data)


@router.post("/import-json", response_model=MonsterOut, status_code=201)
async def import_monster_json(payload: dict = Body(...)):
    """Add a homebrew monster from a pasted JSON statblock (native or Open5e shape)."""
    try:
        return await monster_service.create_monster_from_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{monster_id}", response_model=MonsterOut)
async def update_monster(monster_id: int, data: MonsterUpdate):
    monster = await monster_service.update_monster(monster_id, data)
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")
    return monster


@router.delete("/{monster_id}", status_code=204)
async def delete_monster(monster_id: int):
    deleted = await monster_service.delete_monster(monster_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Monster not found")
