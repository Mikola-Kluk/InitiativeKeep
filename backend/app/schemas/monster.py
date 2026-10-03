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

    # Input limits don't apply on the way out: Open5e imports skip MonsterCreate and
    # some third-party statblocks exceed them (e.g. CON 32) — one such row must not
    # turn the whole list into a 500.
    armor_class: int = 10
    hit_points: int = 1
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    model_config = {"from_attributes": True}


class BulkImportFailure(BaseModel):
    index: int               # position in the submitted list
    name: str | None = None  # the item's name, if it had one
    error: str


class MonsterBulkImportResult(BaseModel):
    imported: list[MonsterOut] = []
    skipped: list[MonsterOut] = []  # identical statblock already in the library
    failed: list[BulkImportFailure] = []
