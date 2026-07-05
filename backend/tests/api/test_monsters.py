import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_list_monsters_empty(client: AsyncClient):
    r = await client.get("/api/v1/monsters/")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_monster_defaults(client: AsyncClient):
    r = await client.post("/api/v1/monsters/", json={"name": "Goblin"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Goblin"
    assert data["source"] == "homebrew"
    assert data["is_homebrew"] is True
    assert data["armor_class"] == 10
    assert data["dex_modifier"] == 0


async def test_dex_modifier_computed(client: AsyncClient):
    r = await client.post("/api/v1/monsters/", json={"name": "Cat", "dexterity": 15})
    assert r.json()["dex_modifier"] == 2  # (15-10)//2


async def test_create_monster_invalid_dexterity(client: AsyncClient):
    r = await client.post("/api/v1/monsters/", json={"name": "X", "dexterity": 99})
    assert r.status_code == 422


async def test_get_monster_not_found(client: AsyncClient):
    r = await client.get("/api/v1/monsters/9999")
    assert r.status_code == 404


async def test_update_monster(client: AsyncClient):
    mid = (await client.post("/api/v1/monsters/", json={"name": "Orc"})).json()["id"]
    r = await client.patch(f"/api/v1/monsters/{mid}", json={"hit_points": 15})
    assert r.status_code == 200
    assert r.json()["hit_points"] == 15
    assert r.json()["name"] == "Orc"  # untouched


async def test_delete_monster(client: AsyncClient):
    mid = (await client.post("/api/v1/monsters/", json={"name": "Tmp"})).json()["id"]
    assert (await client.delete(f"/api/v1/monsters/{mid}")).status_code == 204
    assert (await client.get(f"/api/v1/monsters/{mid}")).status_code == 404


async def test_create_monster_with_defenses(client: AsyncClient):
    r = await client.post(
        "/api/v1/monsters/",
        json={
            "name": "Frost Wraith",
            "damage_vulnerabilities": "fire",
            "damage_resistances": "cold, necrotic",
            "damage_immunities": "poison",
            "condition_immunities": "charmed, frightened",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["damage_vulnerabilities"] == "fire"
    assert data["damage_resistances"] == "cold, necrotic"
    assert data["damage_immunities"] == "poison"
    assert data["condition_immunities"] == "charmed, frightened"


async def test_defenses_default_null(client: AsyncClient):
    data = (await client.post("/api/v1/monsters/", json={"name": "Plain"})).json()
    assert data["damage_resistances"] is None
    assert data["condition_immunities"] is None


async def test_search_filter(client: AsyncClient):
    await client.post("/api/v1/monsters/", json={"name": "Red Dragon"})
    await client.post("/api/v1/monsters/", json={"name": "Goblin"})
    r = await client.get("/api/v1/monsters/", params={"search": "dragon"})
    names = [m["name"] for m in r.json()]
    assert names == ["Red Dragon"]
