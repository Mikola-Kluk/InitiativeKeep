import httpx

from app.config import settings
from app.models.monster import Monster

_USER_AGENT = "InitiativeKeep/1.0"


def _map_open5e_to_fields(m: dict) -> dict:
    """Map an Open5e monster payload to Monster model fields."""
    return {
        "name": m.get("name") or "Unknown",
        "slug": m.get("slug"),
        "source": "open5e",
        "is_homebrew": False,
        "size": m.get("size"),
        "type": m.get("type"),
        "alignment": m.get("alignment"),
        "armor_class": m.get("armor_class") or 10,
        "armor_desc": m.get("armor_desc"),
        "hit_points": m.get("hit_points") or 1,
        "hit_dice": m.get("hit_dice"),
        "speed": m.get("speed") or {},
        "strength": m.get("strength") or 10,
        "dexterity": m.get("dexterity") or 10,
        "constitution": m.get("constitution") or 10,
        "intelligence": m.get("intelligence") or 10,
        "wisdom": m.get("wisdom") or 10,
        "charisma": m.get("charisma") or 10,
        "challenge_rating": m.get("challenge_rating"),
        "cr": m.get("cr"),
        "traits": m.get("special_abilities") or [],
        "actions": m.get("actions") or [],
    }


async def search_open5e(query: str, limit: int = 10) -> list[dict]:
    """Search Open5e monsters. Returns lightweight rows for a picker."""
    if not query.strip():
        return []
    async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as client:
        resp = await client.get(
            f"{settings.OPEN5E_BASE_URL}/v1/monsters/",
            params={"search": query, "limit": limit},
            timeout=15,
        )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "slug": m["slug"],
            "name": m["name"],
            "type": m.get("type"),
            "challenge_rating": m.get("challenge_rating"),
            "hit_points": m.get("hit_points"),
        }
        for m in data.get("results", [])
    ]


async def import_monster(slug: str) -> Monster | None:
    """Fetch a full statblock by slug and store it. Returns existing if already imported."""
    existing = await Monster.get_or_none(slug=slug, source="open5e")
    if existing:
        return existing
    async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as client:
        resp = await client.get(
            f"{settings.OPEN5E_BASE_URL}/v1/monsters/{slug}/", timeout=15
        )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return await Monster.create(**_map_open5e_to_fields(resp.json()))
