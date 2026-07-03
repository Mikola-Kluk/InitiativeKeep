from app.models.encounter import Combatant, Encounter
from app.models.monster import Monster
from app.schemas.encounter import (
    CombatantCreate,
    CombatantUpdate,
    EncounterCreate,
    EncounterUpdate,
)


def _initiative_key(c: Combatant) -> tuple:
    """Sort key: highest initiative first, dex modifier as tiebreak. Unrolled last."""
    rolled = c.initiative is not None
    return (rolled, c.initiative or 0, c.dex_modifier)


async def _sorted_combatants(encounter_id: int) -> list[Combatant]:
    combatants = await Combatant.filter(encounter_id=encounter_id)
    combatants.sort(key=_initiative_key, reverse=True)
    return combatants


async def _load(encounter_id: int) -> Encounter | None:
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    # attach sorted combatants for serialization
    encounter.combatants_ordered = await _sorted_combatants(encounter_id)  # type: ignore[attr-defined]
    return encounter


def _serialize(encounter: Encounter) -> dict:
    return {
        "id": encounter.id,
        "name": encounter.name,
        "notes": encounter.notes,
        "round": encounter.round,
        "current_turn_index": encounter.current_turn_index,
        "combatants": getattr(encounter, "combatants_ordered", []),
    }


# ---- Encounter CRUD ----

async def get_all_encounters() -> list[dict]:
    encounters = await Encounter.all().order_by("-created_at")
    result = []
    for enc in encounters:
        enc.combatants_ordered = await _sorted_combatants(enc.id)  # type: ignore[attr-defined]
        result.append(_serialize(enc))
    return result


async def get_encounter(encounter_id: int) -> dict | None:
    encounter = await _load(encounter_id)
    return _serialize(encounter) if encounter else None


async def create_encounter(data: EncounterCreate) -> dict:
    encounter = await Encounter.create(**data.model_dump())
    encounter.combatants_ordered = []  # type: ignore[attr-defined]
    return _serialize(encounter)


async def update_encounter(encounter_id: int, data: EncounterUpdate) -> dict | None:
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        encounter.update_from_dict(update_data)
        await encounter.save(update_fields=list(update_data.keys()))
    return await get_encounter(encounter_id)


async def delete_encounter(encounter_id: int) -> bool:
    deleted = await Encounter.filter(id=encounter_id).delete()
    return deleted > 0


# ---- Combatants ----

async def add_combatant(encounter_id: int, data: CombatantCreate) -> dict | None:
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None

    fields: dict = {
        "encounter_id": encounter_id,
        "name": data.name,
        "is_pc": data.is_pc,
        "initiative": data.initiative,
        "dex_modifier": data.dex_modifier or 0,
        "armor_class": data.armor_class or 10,
        "max_hp": data.max_hp or 1,
        "current_hp": data.current_hp if data.current_hp is not None else data.max_hp or 1,
    }

    if data.monster_id is not None:
        monster = await Monster.get_or_none(id=data.monster_id)
        if not monster:
            return None
        fields["monster_id"] = monster.id
        fields["name"] = data.name or monster.name
        fields["dex_modifier"] = data.dex_modifier if data.dex_modifier is not None else monster.dex_modifier
        fields["armor_class"] = data.armor_class or monster.armor_class
        fields["max_hp"] = data.max_hp or monster.hit_points
        fields["current_hp"] = data.current_hp if data.current_hp is not None else (data.max_hp or monster.hit_points)

    if not fields["name"]:
        return None

    await Combatant.create(**fields)
    return await get_encounter(encounter_id)


async def update_combatant(
    encounter_id: int, combatant_id: int, data: CombatantUpdate
) -> dict | None:
    combatant = await Combatant.get_or_none(id=combatant_id, encounter_id=encounter_id)
    if not combatant:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        combatant.update_from_dict(update_data)
        await combatant.save(update_fields=list(update_data.keys()))
    return await get_encounter(encounter_id)


async def remove_combatant(encounter_id: int, combatant_id: int) -> dict | None:
    deleted = await Combatant.filter(id=combatant_id, encounter_id=encounter_id).delete()
    if not deleted:
        return None
    return await get_encounter(encounter_id)


# ---- Combat control ----

async def start_combat(encounter_id: int) -> dict | None:
    """Order by initiative and begin at the top. Requires >=1 combatant."""
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    combatants = await _sorted_combatants(encounter_id)
    encounter.round = 1
    encounter.current_turn_index = 0 if combatants else -1
    await encounter.save(update_fields=["round", "current_turn_index"])
    return await get_encounter(encounter_id)


async def next_turn(encounter_id: int) -> dict | None:
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    count = await Combatant.filter(encounter_id=encounter_id).count()
    if count == 0:
        return await get_encounter(encounter_id)
    if encounter.current_turn_index < 0:
        encounter.current_turn_index = 0
        encounter.round = 1
    else:
        encounter.current_turn_index += 1
        if encounter.current_turn_index >= count:
            encounter.current_turn_index = 0
            encounter.round += 1
    await encounter.save(update_fields=["round", "current_turn_index"])
    return await get_encounter(encounter_id)


async def prev_turn(encounter_id: int) -> dict | None:
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    count = await Combatant.filter(encounter_id=encounter_id).count()
    if count == 0:
        return await get_encounter(encounter_id)
    encounter.current_turn_index -= 1
    if encounter.current_turn_index < 0:
        if encounter.round > 1:
            encounter.round -= 1
            encounter.current_turn_index = count - 1
        else:
            encounter.current_turn_index = 0
    await encounter.save(update_fields=["round", "current_turn_index"])
    return await get_encounter(encounter_id)
