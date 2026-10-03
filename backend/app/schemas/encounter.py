from pydantic import BaseModel, Field, model_validator


# ---- Combatant ----

class CombatantCreate(BaseModel):
    # Provide monster_id to spawn from a statblock, or fill fields manually for a PC.
    monster_id: int | None = None
    name: str | None = None
    nick: str | None = Field(default=None, max_length=100)  # tag shown beside the name
    is_pc: bool = False
    level: int | None = Field(default=None, ge=1, le=20)  # PC level
    initiative: int | None = None
    dex_modifier: int | None = None
    armor_class: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=1)
    current_hp: int | None = Field(default=None, ge=0)
    count: int = Field(default=1, ge=1, le=20)  # spawn N copies (monsters)


class CombatantUpdate(BaseModel):
    name: str | None = None
    nick: str | None = Field(default=None, max_length=100)  # null or "" clears it
    level: int | None = Field(default=None, ge=1, le=20)
    initiative: int | None = None
    dex_modifier: int | None = None
    armor_class: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=1)
    current_hp: int | None = Field(default=None, ge=0)
    temp_hp: int | None = Field(default=None, ge=0)
    conditions: list | None = None
    concentrating: bool | None = None
    legendary_actions_remaining: int | None = Field(default=None, ge=0)
    recharge_used: list | None = None  # [{"name", "round"}]


class CombatantOut(BaseModel):
    id: int
    monster_id: int | None = None
    name: str
    nick: str | None = None
    is_pc: bool
    level: int | None = None
    initiative: int | None = None
    dex_modifier: int
    armor_class: int
    max_hp: int
    current_hp: int
    temp_hp: int
    conditions: list
    concentrating: bool
    legendary_actions_max: int
    legendary_actions_remaining: int
    recharge_used: list = []

    model_config = {"from_attributes": True}


# ---- Encounter ----

class EncounterCreate(BaseModel):
    name: str
    notes: str | None = None


class EnemySpec(BaseModel):
    # Pick the statblock by library name (case-insensitive) or by id — exactly one.
    monster: str | None = None
    monster_id: int | None = None
    count: int = Field(default=1, ge=1, le=20)
    name: str | None = None  # override the statblock name
    nick: str | None = Field(default=None, max_length=100)  # tag beside the name, on every copy

    @model_validator(mode="after")
    def _one_reference(self):
        if (self.monster is None) == (self.monster_id is None):
            raise ValueError("Give exactly one of 'monster' (name) or 'monster_id'.")
        if self.monster is not None and not self.monster.strip():
            raise ValueError("'monster' must not be empty.")
        return self


class EncounterPrepare(BaseModel):
    # Encounter + its enemies in one call; PCs join later via POST /{id}/combatants.
    name: str
    notes: str | None = None
    enemies: list[EnemySpec] = Field(default_factory=list, max_length=50)


class EncounterUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None


class EncounterOut(BaseModel):
    id: int
    name: str
    notes: str | None = None
    round: int
    current_turn_index: int
    combatants: list[CombatantOut] = []
    undo_label: str | None = None  # what Undo would revert; None = nothing to undo

    model_config = {"from_attributes": True}
