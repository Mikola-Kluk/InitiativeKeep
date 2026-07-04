from fastapi import APIRouter, HTTPException

from app.schemas.encounter import (
    CombatantCreate,
    CombatantUpdate,
    EncounterCreate,
    EncounterOut,
    EncounterUpdate,
)
from app.services import encounter as encounter_service

router = APIRouter()


@router.get("/", response_model=list[EncounterOut])
async def list_encounters():
    return await encounter_service.get_all_encounters()


@router.get("/{encounter_id}", response_model=EncounterOut)
async def get_encounter(encounter_id: int):
    encounter = await encounter_service.get_encounter(encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


@router.post("/", response_model=EncounterOut, status_code=201)
async def create_encounter(data: EncounterCreate):
    return await encounter_service.create_encounter(data)


@router.patch("/{encounter_id}", response_model=EncounterOut)
async def update_encounter(encounter_id: int, data: EncounterUpdate):
    encounter = await encounter_service.update_encounter(encounter_id, data)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


@router.delete("/{encounter_id}", status_code=204)
async def delete_encounter(encounter_id: int):
    deleted = await encounter_service.delete_encounter(encounter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Encounter not found")


# ---- Combatants ----

@router.post("/{encounter_id}/combatants", response_model=EncounterOut, status_code=201)
async def add_combatant(encounter_id: int, data: CombatantCreate):
    result = await encounter_service.add_combatant(encounter_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Encounter or monster not found, or name missing")
    return result


@router.patch("/{encounter_id}/combatants/{combatant_id}", response_model=EncounterOut)
async def update_combatant(encounter_id: int, combatant_id: int, data: CombatantUpdate):
    result = await encounter_service.update_combatant(encounter_id, combatant_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Combatant not found")
    return result


@router.delete("/{encounter_id}/combatants/{combatant_id}", response_model=EncounterOut)
async def remove_combatant(encounter_id: int, combatant_id: int):
    result = await encounter_service.remove_combatant(encounter_id, combatant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Combatant not found")
    return result


# ---- Combat control ----

@router.post("/{encounter_id}/start", response_model=EncounterOut)
async def start_combat(encounter_id: int):
    result = await encounter_service.start_combat(encounter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return result


@router.post("/{encounter_id}/end", response_model=EncounterOut)
async def end_combat(encounter_id: int):
    result = await encounter_service.end_combat(encounter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return result


@router.post("/{encounter_id}/next-turn", response_model=EncounterOut)
async def next_turn(encounter_id: int):
    result = await encounter_service.next_turn(encounter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return result


@router.post("/{encounter_id}/prev-turn", response_model=EncounterOut)
async def prev_turn(encounter_id: int):
    result = await encounter_service.prev_turn(encounter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return result
