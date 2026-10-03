import re

from tortoise.transactions import in_transaction

from app.models.encounter import Combatant, Encounter, EncounterSnapshot
from app.models.monster import Monster
from app.services import dice
from app.services.monster import statblock_of
from app.schemas.encounter import (
    CombatantCreate,
    CombatantUpdate,
    EncounterCreate,
    EncounterPrepare,
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


def _normalize_recharge(raw: list) -> list[dict]:
    """Keep well-formed [{"name": str, "round": int}] entries, one per ability."""
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw or []:
        if isinstance(item, dict) and item.get("name") and item["name"] not in seen:
            seen.add(item["name"])
            out.append({"name": str(item["name"]), "round": int(item.get("round") or 1)})
    return out


def _clean_nick(raw: str | None) -> str | None:
    """Trim the DM's tag; blank means none."""
    return (raw or "").strip() or None


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


# ---- Undo history ----

UNDO_LIMIT = 50  # snapshots kept per encounter

# combatant columns captured in a snapshot and written back on undo
_SNAPSHOT_FIELDS = (
    "id", "monster_id", "name", "nick", "is_pc", "level", "initiative", "dex_modifier",
    "armor_class", "max_hp", "current_hp", "temp_hp", "conditions", "concentrating",
    "legendary_actions_max", "legendary_actions_remaining", "recharge_used",
)


async def _snapshot(encounter: Encounter, label: str) -> None:
    """Save the encounter's current state so the change about to happen can be undone."""
    combatants = await Combatant.filter(encounter_id=encounter.id)
    state = {
        "round": encounter.round,
        "current_turn_index": encounter.current_turn_index,
        "combatants": [{f: getattr(c, f) for f in _SNAPSHOT_FIELDS} for c in combatants],
    }
    await EncounterSnapshot.create(encounter_id=encounter.id, label=label[:255], state=state)
    stale = await (
        EncounterSnapshot.filter(encounter_id=encounter.id)
        .order_by("-id").offset(UNDO_LIMIT).values_list("id", flat=True)
    )
    if stale:
        await EncounterSnapshot.filter(id__in=list(stale)).delete()


async def _undo_label(encounter_id: int) -> str | None:
    last = await EncounterSnapshot.filter(encounter_id=encounter_id).order_by("-id").first()
    return last.label if last else None


def _describe_update(c: Combatant, changes: dict) -> str:
    """Short human label for a combatant edit, shown on the Undo button."""
    parts = []
    for key, new in changes.items():
        old = getattr(c, key)
        if key == "current_hp":
            parts.append(f"HP {old} → {new}")
        elif key == "temp_hp":
            parts.append(f"temp HP {old} → {new}")
        elif key == "concentrating":
            parts.append("concentration on" if new else "concentration off")
        elif key == "conditions":
            before = {x["name"] for x in _normalize_conditions(old)}
            after = {x["name"] for x in new}
            added, dropped = sorted(after - before), sorted(before - after)
            if added:
                parts.append("+" + ", ".join(added))
            if dropped:
                parts.append("−" + ", ".join(dropped))
            if not added and not dropped:
                parts.append("condition timers")
        elif key == "legendary_actions_remaining":
            parts.append(f"legendary {old} → {new}")
        elif key == "initiative":
            parts.append(f"initiative {old} → {new}")
        elif key == "nick":
            parts.append(f'nick "{new}"' if new else "nick removed")
        elif key == "recharge_used":
            before = {x["name"] for x in _normalize_recharge(old)}
            after = {x["name"] for x in new}
            parts += [f"{n} used" for n in sorted(after - before)]
            parts += [f"{n} recharged" for n in sorted(before - after)]
        else:
            parts.append(key.replace("_", " "))
    return f"{c.name}: {', '.join(parts)}"


async def undo(encounter_id: int) -> dict | None:
    """Restore the most recent snapshot and drop it. Returns None if the
    encounter is missing; raises LookupError if there is nothing to undo."""
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None
    snap = await EncounterSnapshot.filter(encounter_id=encounter_id).order_by("-id").first()
    if not snap:
        raise LookupError("Nothing to undo.")

    state = snap.state
    rows = {row["id"]: row for row in state["combatants"]}
    # a statblock deleted since the snapshot can't be linked again
    monster_ids = [r["monster_id"] for r in rows.values() if r["monster_id"] is not None]
    live_monsters = (
        set(await Monster.filter(id__in=monster_ids).values_list("id", flat=True))
        if monster_ids else set()
    )

    async with in_transaction():
        await Combatant.filter(encounter_id=encounter_id).exclude(id__in=list(rows)).delete()
        current = {c.id: c for c in await Combatant.filter(encounter_id=encounter_id)}
        for cid, row in rows.items():
            data = {k: v for k, v in row.items() if k != "id"}
            if data["monster_id"] not in live_monsters:
                data["monster_id"] = None
            if cid in current:
                c = current[cid]
                c.update_from_dict(data)
                await c.save(update_fields=list(data))
            else:
                # removed since the snapshot: bring it back under its old id
                await Combatant.create(id=cid, encounter_id=encounter_id, **data)
        encounter.round = state["round"]
        encounter.current_turn_index = state["current_turn_index"]
        await encounter.save(update_fields=["round", "current_turn_index"])
        await snap.delete()
    return await get_encounter(encounter_id)


def _serialize(encounter: Encounter) -> dict:
    return {
        "id": encounter.id,
        "name": encounter.name,
        "notes": encounter.notes,
        "round": encounter.round,
        "current_turn_index": encounter.current_turn_index,
        "combatants": getattr(encounter, "combatants_ordered", []),
        "undo_label": getattr(encounter, "undo_label", None),
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
    if not encounter:
        return None
    encounter.undo_label = await _undo_label(encounter_id)  # type: ignore[attr-defined]
    return _serialize(encounter)


async def create_encounter(data: EncounterCreate) -> dict:
    encounter = await Encounter.create(**data.model_dump())
    encounter.combatants_ordered = []  # type: ignore[attr-defined]
    return _serialize(encounter)


def _same_statblock(monsters: list[Monster]) -> bool:
    """True if these library rows are copies of one statblock (e.g. pasted twice)."""
    first = statblock_of(monsters[0])
    return all(statblock_of(m) == first for m in monsters[1:])


def _describe_monster(m: Monster) -> str:
    origin = m.slug or m.source
    return f"id {m.id} ({origin}, CR {m.challenge_rating or '—'}, {m.hit_points} HP)"


async def prepare_encounter(data: EncounterPrepare) -> dict:
    """Create an encounter already stocked with its enemies (combat not started).
    Enemies name their statblock by library name (case-insensitive) or by id.
    A name shared by identical copies resolves to the oldest copy.
    All-or-nothing: raises LookupError if a monster is unknown, ValueError if a
    name matches several different statblocks. No undo history — there is nothing before a
    fresh encounter to go back to."""
    ids = {e.monster_id for e in data.enemies if e.monster_id is not None}
    by_id = {m.id: m for m in await Monster.filter(id__in=list(ids))} if ids else {}
    missing = [str(i) for i in sorted(ids - set(by_id))]

    by_name: dict[str, Monster] = {}
    for key in {e.monster.strip().lower() for e in data.enemies if e.monster is not None}:
        matches = await Monster.filter(name__iexact=key).order_by("id")
        if len(matches) > 1 and not _same_statblock(matches):
            found = "; ".join(_describe_monster(m) for m in matches)
            raise ValueError(
                f"Monster name '{matches[0].name}' matches different statblocks: "
                f"{found} — use monster_id instead."
            )
        if matches:
            by_name[key] = matches[0]
        else:
            missing.append(f"'{key}'")
    if missing:
        raise LookupError(f"Monster not found: {', '.join(missing)}")

    async with in_transaction():
        encounter = await Encounter.create(name=data.name, notes=data.notes)
        for enemy in data.enemies:
            monster = (
                by_id[enemy.monster_id] if enemy.monster_id is not None
                else by_name[enemy.monster.strip().lower()]
            )
            fields = _monster_fields(monster)
            fields["encounter_id"] = encounter.id
            fields["nick"] = _clean_nick(enemy.nick)
            base = _base_name(enemy.name or monster.name)
            for _ in range(enemy.count):
                fields["name"] = await _dedupe_name(encounter.id, base)
                await Combatant.create(**fields)
    return await get_encounter(encounter.id)


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

def _monster_fields(monster: Monster) -> dict:
    """Combatant columns taken straight from a statblock."""
    fields: dict = {
        "monster_id": monster.id,
        "name": monster.name,
        "dex_modifier": monster.dex_modifier,
        "armor_class": monster.armor_class,
        "max_hp": monster.hit_points,
        "current_hp": monster.hit_points,
    }
    if monster.legendary_actions:
        # 5e default: 3 legendary actions per round
        fields["legendary_actions_max"] = 3
        fields["legendary_actions_remaining"] = 3
    return fields


async def add_combatant(encounter_id: int, data: CombatantCreate) -> dict | None:
    encounter = await Encounter.get_or_none(id=encounter_id)
    if not encounter:
        return None

    fields: dict = {
        "encounter_id": encounter_id,
        "name": data.name,
        "nick": _clean_nick(data.nick),
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
        fields.update(_monster_fields(monster))
        fields["name"] = data.name or monster.name
        if data.dex_modifier is not None:
            fields["dex_modifier"] = data.dex_modifier
        fields["armor_class"] = data.armor_class or monster.armor_class
        fields["max_hp"] = data.max_hp or monster.hit_points
        fields["current_hp"] = data.current_hp if data.current_hp is not None else fields["max_hp"]

    if not fields["name"]:
        return None

    base = _base_name(fields["name"])
    await _snapshot(encounter, f"add {base}" + (f" ×{data.count}" if data.count > 1 else ""))
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
    if "recharge_used" in update_data:
        update_data["recharge_used"] = _normalize_recharge(update_data["recharge_used"])
    if "nick" in update_data:
        update_data["nick"] = _clean_nick(update_data["nick"])
    # only real changes go into the undo history
    update_data = {k: v for k, v in update_data.items() if getattr(combatant, k) != v}
    if update_data:
        encounter = await Encounter.get(id=encounter_id)
        await _snapshot(encounter, _describe_update(combatant, update_data))
        combatant.update_from_dict(update_data)
        await combatant.save(update_fields=list(update_data.keys()))
    return await get_encounter(encounter_id)


async def remove_combatant(encounter_id: int, combatant_id: int) -> dict | None:
    combatant = await Combatant.get_or_none(id=combatant_id, encounter_id=encounter_id)
    if not combatant:
        return None
    encounter = await Encounter.get(id=encounter_id)
    await _snapshot(encounter, f"remove {combatant.name}")
    await combatant.delete()
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

    await _snapshot(encounter, "start fight")
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
        if c.recharge_used:
            # a fresh fight starts with every recharge ability ready
            c.recharge_used = []
            changed.append("recharge_used")
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
    await _snapshot(encounter, "end fight")
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
    await _snapshot(encounter, f"next turn (round {encounter.round})")
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
    await _snapshot(encounter, f"previous turn (round {encounter.round})")
    encounter.current_turn_index -= 1
    if encounter.current_turn_index < 0:
        if encounter.round > 1:
            encounter.round -= 1
            encounter.current_turn_index = count - 1
        else:
            encounter.current_turn_index = 0
    await encounter.save(update_fields=["round", "current_turn_index"])
    return await get_encounter(encounter_id)
