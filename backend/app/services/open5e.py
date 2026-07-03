import math

import httpx

from app.config import settings
from app.models.monster import Monster

_USER_AGENT = "InitiativeKeep/1.0"
_PAGE_SIZE = 50


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


def _light_row(m: dict) -> dict:
    return {
        "slug": m["slug"],
        "name": m["name"],
        "type": m.get("type"),
        "challenge_rating": m.get("challenge_rating"),
        "cr": m.get("cr"),
        "hit_points": m.get("hit_points"),
        "document": m.get("document__slug"),
    }


async def browse_open5e(
    query: str | None = None,
    cr: str | None = None,
    type: str | None = None,
    document: str | None = None,
    page: int = 1,
    page_size: int = _PAGE_SIZE,
) -> dict:
    """Paginated, filtered browse of Open5e monsters. Returns light rows for a picker."""
    params: dict = {"limit": page_size, "page": max(page, 1), "ordering": "name"}
    if query and query.strip():
        params["search"] = query.strip()
    if cr is not None and cr != "":
        params["cr"] = cr
    if type:
        params["type"] = type
    if document:
        params["document__slug"] = document

    async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as client:
        resp = await client.get(
            f"{settings.OPEN5E_BASE_URL}/v1/monsters/", params=params, timeout=15
        )
    resp.raise_for_status()
    data = resp.json()
    count = data.get("count", 0)
    return {
        "count": count,
        "page": params["page"],
        "num_pages": max(1, math.ceil(count / page_size)) if count else 1,
        "results": [_light_row(m) for m in data.get("results", [])],
    }


async def list_sources() -> list[dict]:
    """List Open5e document sources (for a filter dropdown)."""
    async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as client:
        resp = await client.get(
            f"{settings.OPEN5E_BASE_URL}/v1/documents/",
            params={"limit": 50},
            timeout=15,
        )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"slug": d.get("slug"), "name": d.get("name") or d.get("title")}
        for d in data.get("results", [])
        if d.get("slug")
    ]


async def preview_open5e(slug: str) -> dict | None:
    """Fetch a full statblock by slug WITHOUT saving it — for previewing stats
    before import. Shaped like MonsterOut (id=0, not persisted)."""
    async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}) as client:
        resp = await client.get(
            f"{settings.OPEN5E_BASE_URL}/v1/monsters/{slug}/", timeout=15
        )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    fields = _map_open5e_to_fields(resp.json())
    return {**fields, "id": 0, "dex_modifier": (fields["dexterity"] - 10) // 2}


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


async def import_many(slugs: list[str]) -> dict:
    """Import a batch of slugs. Idempotent per slug. Returns imported/failed lists."""
    imported: list[str] = []
    failed: list[str] = []
    for slug in slugs:
        try:
            monster = await import_monster(slug)
        except httpx.HTTPError:
            failed.append(slug)
            continue
        (imported if monster else failed).append(slug)
    return {"imported": imported, "failed": failed}
