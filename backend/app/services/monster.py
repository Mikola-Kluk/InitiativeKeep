from app.models.monster import Monster
from app.schemas.monster import MonsterCreate, MonsterUpdate


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


async def create_monster_from_json(raw: dict) -> Monster:
    """Validate a pasted JSON statblock and store it as homebrew."""
    data = MonsterCreate(**normalize_monster_payload(raw))
    return await create_monster(data)


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
