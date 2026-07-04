from tortoise import fields
from tortoise.models import Model


class Character(Model):
    """A saved player character (party roster). Reusable across encounters —
    pick one to drop it into a fight instead of re-typing HP and level."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    max_hp = fields.IntField(default=1)
    level = fields.IntField(default=1)  # drives encounter difficulty budget

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "characters"
