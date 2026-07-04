from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterUpdate


async def get_all_characters() -> list[Character]:
    return await Character.all().order_by("name")


async def create_character(data: CharacterCreate) -> Character:
    return await Character.create(**data.model_dump())


async def update_character(character_id: int, data: CharacterUpdate) -> Character | None:
    character = await Character.get_or_none(id=character_id)
    if not character:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        character.update_from_dict(update_data)
        await character.save(update_fields=list(update_data.keys()))
    return character


async def delete_character(character_id: int) -> bool:
    deleted = await Character.filter(id=character_id).delete()
    return deleted > 0
