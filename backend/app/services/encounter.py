import re

from app.models.encounter import Combatant, Encounter
from app.models.monster import Monster
from app.services import dice
from app.schemas.encounter import (
    CombatantCreate,
    CombatantUpdate,
    EncounterCreate,
    EncounterUpdate,
)

_NUM_SUFFIX = re.compile(r"\s*\((\d+)\)$")


def _base_name(name: str) -> str:
    """'Goblin (2)' -> 'Goblin'."""
    return _NUM_SUFFIX.sub("", name)


async def _dedupe_name(encounter_id: int, base: str) -> str:
    """Number duplicate combatants: first stays 'Goblin', a second turns the pair
    into 'Goblin (1)' / 'Goblin (2)', and so on."""
    siblings = [
        c for c in await Combatant.filter(encounter_id=encounter_id)
        if _base_name(c.name) == base
    ]
    if not siblings:
        return base

    numbers = []
    for c in siblings:
        m = _NUM_SUFFIX.search(c.name)
        numbers.append(int(m.group(1)) if m else None)

    if len(siblings) == 1 and numbers[0] is None:
        # promote the lone unnumbered one to "(1)"
        siblings[0].name = f"{base} (1)"
        await siblings[0].save(update_fields=["name"])
        return f"{base} (2)"

    used = [n for n in numbers if n is not None]
    return f"{base} ({(max(used) + 1) if used else len(siblings) + 1})"


def _normalize_conditions(raw: list) -> list[dict]:
    """Accept legacy plain strings and dicts; always return [{"name", "rounds"}].
    rounds = remaining rounds (int) or None for indefinite."""
    out: list[dict] = []
    for item in raw or []:
        if isinstance(item, str):
            out.append({"name": item, "rounds": None})
        elif isinstance(item, dict) and item.get("name"):
            rounds = item.get("rounds")
            out.append({"name": item["name"], "rounds": int(rounds) if rounds is not None else None})
    return out


def _initiative_key(c: Combatant) -> tuple:
    """Sort key: highest initiative first, dex modifier as tiebreak. Unrolled last."""
    rolled = c.initiative is not None
    return (rolled, c.initiative or 0, c.dex_modifier)


async def _sorted_combatants(encounter_id: int) -> list[Combatant]:
    combatants = await Combatant.filter(encounter_id=encounter_id)
    for c in combatants:
        c.conditions = _normalize_conditions(c.conditions)
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
        "level": data.level,
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
        if monster.legendary_actions:
            # 5e default: 3 legendary actions per round
            fields["legendary_actions_max"] = 3
            fields["legendary_actions_remaining"] = 3

    if not fields["name"]:
        return None

    base = _base_name(fields["name"])
    for _ in range(data.count):
        fields["name"] = await _dedupe_name(encounter_id, base)
        await Combatant.create(**fields)
    return await get_encounter(encounter_id)


async def update_combatant(
    encounter_id: int, combatant_id: int, data: CombatantUpdate
) -> dict | None:
    combatant = await Combatant.get_or_none(id=combatant_id, encounter_id=encounter_id)
    if not combatant:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if "conditions" in update_data:
        update_data["conditions"] = _normalize_conditions(update_data["conditions"])
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

async def _tick_condition_durations(encounter_id: int) -> None:
    """End of round: count down timed conditions, drop the ones that expire."""
    for c in await Combatant.filter(encounter_id=encounter_id):
        raw = c.conditions or []
        ticked = []
        for cond in _normalize_conditions(raw):
            if cond["rounds"] is None:
                ticked.append(cond)
            elif cond["rounds"] > 1:
                ticked.append({"name": cond["name"], "rounds": cond["rounds"] - 1})
        if ticked != raw:
            c.conditions = ticked
            await c.save(update_fields=["conditions"])


async def _refill_legendary(encounter_id: int, turn_index: int) -> None:
    """Legendary action pool refills at the start of the creature's own turn."""
    combatants = await _sorted_combatants(encounter_id)
    if 0 <= turn_index < len(combatants):
        c = combatants[turn_index]
        if c.legendary_actions_max and c.legendary_actions_remaining != c.legendary_actions_max:
            c.legendary_actions_remaining = c.legendary_actions_max
            await c.save(update_fields=["legendary_actions_remaining"])


async def start_combat(encounter_id: int) -> dict | None:
    """Begin combat: roll initiative for anyone who hasn't got one, reroll monster
    HP, order by initiative, start at the top.

    - Only combatants with no initiative yet get rolled (d20 + dex_modifier);
      a value entered during prep is kept.
    - From a statblock (monster_id set) with hit_dice: HP rolled from hit_dice
    PCs keep their entered HP.
    """
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None

    combatants = await Combatant.filter(encounter_id=encounter_id).prefetch_related("monster")
    for c in combatants:
        changed: list[str] = []
        if c.initiative is None:
            c.initiative = dice.roll_initiative(c.dex_modifier)
            changed.append("initiative")
        if c.monster_id and c.monster and c.monster.hit_dice:
            hp = dice.roll_expr(c.monster.hit_dice, default=c.max_hp)
            c.max_hp = hp
            c.current_hp = hp
            changed += ["max_hp", "current_hp"]
        if c.legendary_actions_max and c.legendary_actions_remaining != c.legendary_actions_max:
            c.legendary_actions_remaining = c.legendary_actions_max
            changed.append("legendary_actions_remaining")
        if changed:
            await c.save(update_fields=changed)

    encounter.round = 1
    encounter.current_turn_index = 0 if combatants else -1
    await encounter.save(update_fields=["round", "current_turn_index"])
    return await get_encounter(encounter_id)


async def end_combat(encounter_id: int) -> dict | None:
    """End combat: reset to the not-started state (round 1, no active turn).

    HP and conditions are left untouched so the aftermath is preserved.
    """
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    encounter.round = 1
    encounter.current_turn_index = -1
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
            await _tick_condition_durations(encounter_id)
    await encounter.save(update_fields=["round", "current_turn_index"])
    await _refill_legendary(encounter_id, encounter.current_turn_index)
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
