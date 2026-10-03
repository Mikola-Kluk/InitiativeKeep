from pydantic import ValidationError

from app.models.monster import Monster
from app.schemas.monster import BulkImportFailure, MonsterCreate, MonsterUpdate

BULK_IMPORT_LIMIT = 500


def normalize_monster_payload(raw: dict) -> dict:
    """Coerce an arbitrary pasted JSON into MonsterCreate kwargs.

    Accepts both the native shape (this app's own `traits`) and an Open5e
    statblock (which calls traits `special_abilities`). Unknown keys and nulls
    are dropped so the schema's defaults apply."""
    if not isinstance(raw, dict):
        raise ValueError("JSON must be an object (a single statblock).")
    data = dict(raw)
    if "traits" not in data and "special_abilities" in data:
        data["traits"] = data["special_abilities"]
    allowed = set(MonsterCreate.model_fields)
    return {k: v for k, v in data.items() if k in allowed and v is not None}


# what the creature is, as opposed to where the row came from (id, slug, source, ...)
_STATBLOCK_FIELDS = tuple(f for f in MonsterCreate.model_fields if f != "name")


def statblock_of(monster: Monster | MonsterCreate) -> dict:
    """The stats of a statblock, for telling copies from namesakes."""
    return {f: getattr(monster, f) for f in _STATBLOCK_FIELDS}


async def find_identical(data: MonsterCreate) -> Monster | None:
    """The oldest library statblock with this name (any letter case) and the same stats."""
    wanted = statblock_of(data)
    for existing in await Monster.filter(name__iexact=data.name.strip()).order_by("id"):
        if statblock_of(existing) == wanted:
            return existing
    return None


async def create_monster_from_json(raw: dict) -> tuple[Monster, bool]:
    """Validate a pasted JSON statblock and store it as homebrew. A statblock the
    library already holds is not stored again. Returns (monster, created)."""
    data = MonsterCreate(**normalize_monster_payload(raw))
    existing = await find_identical(data)
    if existing:
        return existing, False
    return await create_monster(data), True


def _unwrap_monster_list(raw) -> list:
    """Accept a bare list, or an object wrapping one (`results` as in an Open5e
    page, or `monsters`)."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("results", "monsters"):
            if isinstance(raw.get(key), list):
                return raw[key]
    raise ValueError(
        'JSON must be a list of statblocks, or an object with a "results" or "monsters" list.'
    )


def _format_validation_error(e: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc']) or 'body'}: {err['msg']}"
        for err in e.errors()
    )


async def create_monsters_from_json(
    raw,
) -> tuple[list[Monster], list[Monster], list[BulkImportFailure]]:
    """Store many pasted statblocks as homebrew. Each item is validated on its
    own: valid ones are saved, invalid ones are reported (not a 422 for all).
    Returns (imported, skipped, failed); skipped = already in the library."""
    items = _unwrap_monster_list(raw)
    if not items:
        raise ValueError("The list is empty.")
    if len(items) > BULK_IMPORT_LIMIT:
        raise ValueError(f"Too many statblocks ({len(items)}); the limit is {BULK_IMPORT_LIMIT}.")

    imported: list[Monster] = []
    skipped: list[Monster] = []
    failed: list[BulkImportFailure] = []
    for i, item in enumerate(items):
        name = item.get("name") if isinstance(item, dict) else None
        try:
            monster, created = await create_monster_from_json(item)
            (imported if created else skipped).append(monster)
        except ValidationError as e:
            failed.append(BulkImportFailure(index=i, name=name, error=_format_validation_error(e)))
        except ValueError as e:
            failed.append(BulkImportFailure(index=i, name=name, error=str(e)))
    return imported, skipped, failed


async def get_all_monsters(search: str | None = None) -> list[Monster]:
    qs = Monster.all().order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    return await qs


async def get_monster(monster_id: int) -> Monster | None:
    return await Monster.get_or_none(id=monster_id)


async def create_monster(data: MonsterCreate) -> Monster:
    return await Monster.create(
        **data.model_dump(), source="homebrew", is_homebrew=True
    )


async def update_monster(monster_id: int, data: MonsterUpdate) -> Monster | None:
    monster = await Monster.get_or_none(id=monster_id)
    if not monster:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        monster.update_from_dict(update_data)
        await monster.save(update_fields=list(update_data.keys()))
    return monster


async def delete_monster(monster_id: int) -> bool:
    deleted = await Monster.filter(id=monster_id).delete()
    return deleted > 0
