import pytest

from app.models.encounter import Encounter
from app.models.monster import Monster

pytestmark = pytest.mark.anyio

URL = "/api/v1/encounters/prepare"


async def test_prepare_creates_encounter_with_enemies(client):
    goblin = await Monster.create(name="Goblin", armor_class=15, hit_points=7, dexterity=14)
    dragon = await Monster.create(
        name="Dragon", hit_points=200, legendary_actions=[{"name": "Tail", "desc": "..."}]
    )

    resp = await client.post(URL, json={
        "name": "Ambush",
        "notes": "at the bridge",
        "enemies": [
            {"monster_id": goblin.id, "count": 3},
            {"monster_id": dragon.id, "name": "Old Smoky"},
        ],
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Ambush"
    assert body["notes"] == "at the bridge"
    assert body["current_turn_index"] == -1
    assert body["undo_label"] is None

    by_name = {c["name"]: c for c in body["combatants"]}
    assert set(by_name) == {"Goblin (1)", "Goblin (2)", "Goblin (3)", "Old Smoky"}
    assert all(not c["is_pc"] and c["initiative"] is None for c in by_name.values())
    gob = by_name["Goblin (1)"]
    assert (gob["monster_id"], gob["armor_class"], gob["max_hp"], gob["current_hp"]) == (goblin.id, 15, 7, 7)
    assert gob["dex_modifier"] == 2
    assert by_name["Old Smoky"]["legendary_actions_max"] == 3


async def test_prepare_then_add_pc(client):
    goblin = await Monster.create(name="Goblin", hit_points=7)
    enc = (await client.post(URL, json={"name": "Ambush", "enemies": [{"monster_id": goblin.id}]})).json()

    resp = await client.post(
        f"/api/v1/encounters/{enc['id']}/combatants",
        json={"name": "Aria", "is_pc": True, "level": 5},
    )

    assert resp.status_code == 201
    names = {c["name"]: c["is_pc"] for c in resp.json()["combatants"]}
    assert names == {"Goblin": False, "Aria": True}


async def test_prepare_without_enemies(client):
    resp = await client.post(URL, json={"name": "Empty"})
    assert resp.status_code == 201
    assert resp.json()["combatants"] == []


async def test_prepare_unknown_monster_creates_nothing(client):
    goblin = await Monster.create(name="Goblin")
    resp = await client.post(URL, json={
        "name": "Broken",
        "enemies": [{"monster_id": goblin.id}, {"monster_id": 99999}],
    })
    assert resp.status_code == 404
    assert "99999" in resp.json()["detail"]
    assert await Encounter.all().count() == 0


async def test_prepare_by_monster_name(client):
    goblin = await Monster.create(name="Goblin", hit_points=7)
    wolf = await Monster.create(name="Dire Wolf", hit_points=37)

    resp = await client.post(URL, json={
        "name": "Pack",
        "enemies": [
            {"monster": "goblin", "count": 2},
            {"monster": " Dire Wolf ", "name": "Fang"},
            {"monster_id": goblin.id},
        ],
    })

    assert resp.status_code == 201
    got = {c["name"]: c["monster_id"] for c in resp.json()["combatants"]}
    assert got == {
        "Goblin (1)": goblin.id, "Goblin (2)": goblin.id, "Goblin (3)": goblin.id, "Fang": wolf.id,
    }


async def test_prepare_unknown_monster_name_creates_nothing(client):
    resp = await client.post(URL, json={"name": "Broken", "enemies": [{"monster": "Tarrasque"}]})
    assert resp.status_code == 404
    assert "tarrasque" in resp.json()["detail"]
    assert await Encounter.all().count() == 0


async def test_prepare_ambiguous_monster_name(client):
    a = await Monster.create(name="Goblin")
    b = await Monster.create(name="goblin")
    resp = await client.post(URL, json={"name": "Twins", "enemies": [{"monster": "Goblin"}]})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert str(a.id) in detail and str(b.id) in detail
    assert await Encounter.all().count() == 0


@pytest.mark.parametrize("enemy", [
    {},
    {"monster": "Goblin", "monster_id": 1},
    {"monster": "  "},
])
async def test_prepare_needs_exactly_one_reference(client, enemy):
    resp = await client.post(URL, json={"name": "Bad", "enemies": [enemy]})
    assert resp.status_code == 422


async def test_prepare_rejects_bad_count(client):
    goblin = await Monster.create(name="Goblin")
    resp = await client.post(URL, json={"name": "Horde", "enemies": [{"monster_id": goblin.id, "count": 21}]})
    assert resp.status_code == 422
