from fastapi import APIRouter, HTTPException

from app.schemas.character import CharacterCreate, CharacterOut, CharacterUpdate
from app.services import character as character_service

router = APIRouter()


@router.get("/", response_model=list[CharacterOut])
async def list_characters():
    return await character_service.get_all_characters()


@router.post("/", response_model=CharacterOut, status_code=201)
async def create_character(data: CharacterCreate):
    return await character_service.create_character(data)


@router.patch("/{character_id}", response_model=CharacterOut)
async def update_character(character_id: int, data: CharacterUpdate):
    character = await character_service.update_character(character_id, data)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.delete("/{character_id}", status_code=204)
async def delete_character(character_id: int):
    deleted = await character_service.delete_character(character_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Character not found")
