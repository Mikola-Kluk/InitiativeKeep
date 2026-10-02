from tortoise import fields
from tortoise.models import Model


class Encounter(Model):
    """A single combat. Holds ordered combatants and turn/round state."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    notes = fields.TextField(null=True)

    round = fields.IntField(default=1)
    # index into initiative-sorted combatants; -1 = combat not started
    current_turn_index = fields.IntField(default=-1)

    created_at = fields.DatetimeField(auto_now_add=True)

    combatants: fields.ReverseRelation["Combatant"]

    class Meta:
        table = "encounters"


class Combatant(Model):
    """A participant in an encounter — a PC or a monster instance."""

    id = fields.IntField(primary_key=True)
    encounter = fields.ForeignKeyField(
        "models.Encounter", related_name="combatants", on_delete=fields.CASCADE
    )
    # optional link to a statblock; null for a plain PC line
    monster = fields.ForeignKeyField(
        "models.Monster", related_name="combatants", null=True, on_delete=fields.SET_NULL
    )

    name = fields.CharField(max_length=255)
    is_pc = fields.BooleanField(default=False)
    level = fields.IntField(null=True)  # PC level; drives encounter difficulty budget

    initiative = fields.IntField(null=True)  # rolled total; null = not yet rolled
    dex_modifier = fields.IntField(default=0)  # tiebreak on initiative

    armor_class = fields.IntField(default=10)
    max_hp = fields.IntField(default=1)
    current_hp = fields.IntField(default=1)
    temp_hp = fields.IntField(default=0)

    conditions = fields.JSONField(default=list)  # [{"name": "poisoned", "rounds": 2|None}, ...]
    concentrating = fields.BooleanField(default=False)

    # legendary actions (bosses): pool refills at the start of the creature's turn
    legendary_actions_max = fields.IntField(default=0)
    legendary_actions_remaining = fields.IntField(default=0)

    # spent recharge abilities: [{"name": "Fire Breath", "round": 2}]; the DM rolls
    # the d6 at the start of the creature's turn and clears the entry on a hit.
    # Added after launch — init_db.py adds the column to existing databases.
    recharge_used = fields.JSONField(default=list)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "combatants"


class EncounterSnapshot(Model):
    """Full encounter state captured right before a change, for Undo.

    `state` = {"round", "current_turn_index", "combatants": [row dicts]};
    `label` says what the change after it was, e.g. "Goblin (2): HP 7 → 2"."""

    id = fields.IntField(primary_key=True)
    encounter = fields.ForeignKeyField(
        "models.Encounter", related_name="snapshots", on_delete=fields.CASCADE
    )
    label = fields.CharField(max_length=255)
    state = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "encounter_snapshots"
