from pydantic import BaseModel, Field


class CharacterCreate(BaseModel):
    name: str
    max_hp: int = Field(default=1, ge=1)
    level: int = Field(default=1, ge=1, le=20)


class CharacterUpdate(BaseModel):
    name: str | None = None
    max_hp: int | None = Field(default=None, ge=1)
    level: int | None = Field(default=None, ge=1, le=20)


class CharacterOut(BaseModel):
    id: int
    name: str
    max_hp: int
    level: int

    model_config = {"from_attributes": True}
