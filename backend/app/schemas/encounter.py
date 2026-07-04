from pydantic import BaseModel, Field


# ---- Combatant ----

class CombatantCreate(BaseModel):
    # Provide monster_id to spawn from a statblock, or fill fields manually for a PC.
    monster_id: int | None = None
    name: str | None = None
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


class CombatantOut(BaseModel):
    id: int
    monster_id: int | None = None
    name: str
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

    model_config = {"from_attributes": True}


# ---- Encounter ----

class EncounterCreate(BaseModel):
    name: str
    notes: str | None = None


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

    model_config = {"from_attributes": True}
