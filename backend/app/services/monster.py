from app.models.monster import Monster
from app.schemas.monster import MonsterCreate, MonsterUpdate


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
