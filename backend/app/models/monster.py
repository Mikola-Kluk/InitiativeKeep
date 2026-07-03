from tortoise import fields
from tortoise.models import Model


class Monster(Model):
    """A D&D statblock. Either imported from Open5e or homebrew."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    slug = fields.CharField(max_length=255, null=True)  # open5e slug; null for homebrew
    source = fields.CharField(max_length=100, default="homebrew")  # "open5e" | "homebrew"
    is_homebrew = fields.BooleanField(default=True)

    size = fields.CharField(max_length=20, null=True)  # Tiny..Gargantuan
    type = fields.CharField(max_length=100, null=True)  # e.g. "dragon"
    alignment = fields.CharField(max_length=100, null=True)

    armor_class = fields.IntField(default=10)
    armor_desc = fields.CharField(max_length=255, null=True)
    hit_points = fields.IntField(default=1)
    hit_dice = fields.CharField(max_length=50, null=True)  # e.g. "18d10+36"
    speed = fields.JSONField(default=dict)  # {"walk": 30, "fly": 60}

    strength = fields.IntField(default=10)
    dexterity = fields.IntField(default=10)
    constitution = fields.IntField(default=10)
    intelligence = fields.IntField(default=10)
    wisdom = fields.IntField(default=10)
    charisma = fields.IntField(default=10)

    challenge_rating = fields.CharField(max_length=10, null=True)  # "1/4", "5", ...
    cr = fields.FloatField(null=True)  # numeric CR for sorting

    traits = fields.JSONField(default=list)  # [{"name","desc"}]
    actions = fields.JSONField(default=list)  # [{"name","desc"}]

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "monsters"

    @property
    def dex_modifier(self) -> int:
        return (self.dexterity - 10) // 2
