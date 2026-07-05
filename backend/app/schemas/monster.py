from pydantic import BaseModel, Field


class MonsterBase(BaseModel):
    name: str
    size: str | None = None
    type: str | None = None
    alignment: str | None = None

    armor_class: int = Field(default=10, ge=0)
    armor_desc: str | None = None
    hit_points: int = Field(default=1, ge=1)
    hit_dice: str | None = None
    speed: dict = Field(default_factory=dict)

    strength: int = Field(default=10, ge=1, le=30)
    dexterity: int = Field(default=10, ge=1, le=30)
    constitution: int = Field(default=10, ge=1, le=30)
    intelligence: int = Field(default=10, ge=1, le=30)
    wisdom: int = Field(default=10, ge=1, le=30)
    charisma: int = Field(default=10, ge=1, le=30)

    challenge_rating: str | None = None
    cr: float | None = None

    damage_vulnerabilities: str | None = None
    damage_resistances: str | None = None
    damage_immunities: str | None = None
    condition_immunities: str | None = None
    senses: str | None = None
    languages: str | None = None

    traits: list = Field(default_factory=list)
    actions: list = Field(default_factory=list)
    reactions: list = Field(default_factory=list)
    legendary_desc: str | None = None
    legendary_actions: list = Field(default_factory=list)


class MonsterCreate(MonsterBase):
    pass


class MonsterUpdate(BaseModel):
    name: str | None = None
    size: str | None = None
    type: str | None = None
    alignment: str | None = None
    armor_class: int | None = Field(default=None, ge=0)
    armor_desc: str | None = None
    hit_points: int | None = Field(default=None, ge=1)
    hit_dice: str | None = None
    speed: dict | None = None
    strength: int | None = Field(default=None, ge=1, le=30)
    dexterity: int | None = Field(default=None, ge=1, le=30)
    constitution: int | None = Field(default=None, ge=1, le=30)
    intelligence: int | None = Field(default=None, ge=1, le=30)
    wisdom: int | None = Field(default=None, ge=1, le=30)
    charisma: int | None = Field(default=None, ge=1, le=30)
    challenge_rating: str | None = None
    cr: float | None = None
    damage_vulnerabilities: str | None = None
    damage_resistances: str | None = None
    damage_immunities: str | None = None
    condition_immunities: str | None = None
    senses: str | None = None
    languages: str | None = None
    traits: list | None = None
    actions: list | None = None
    reactions: list | None = None
    legendary_desc: str | None = None
    legendary_actions: list | None = None


class MonsterOut(MonsterBase):
    id: int
    slug: str | None = None
    source: str
    is_homebrew: bool
    dex_modifier: int

    model_config = {"from_attributes": True}
