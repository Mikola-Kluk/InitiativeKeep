import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _make_encounter(client: AsyncClient, name="Fight") -> int:
    return (await client.post("/api/v1/encounters/", json={"name": name})).json()["id"]


async def _add(client, eid, **body):
    return await client.post(f"/api/v1/encounters/{eid}/combatants", json=body)


async def test_create_encounter_defaults(client: AsyncClient):
    r = await client.post("/api/v1/encounters/", json={"name": "Ambush"})
    assert r.status_code == 201
    data = r.json()
    assert data["round"] == 1
    assert data["current_turn_index"] == -1
    assert data["combatants"] == []


async def test_add_pc_combatant(client: AsyncClient):
    eid = await _make_encounter(client)
    r = await _add(client, eid, name="Aragorn", is_pc=True, initiative=17, max_hp=40)
    assert r.status_code == 201
    c = r.json()["combatants"][0]
    assert c["name"] == "Aragorn"
    assert c["is_pc"] is True
    assert c["current_hp"] == 40  # defaults from max_hp


async def test_add_combatant_from_monster(client: AsyncClient):
    mid = (await client.post(
        "/api/v1/monsters/",
        json={"name": "Goblin", "hit_points": 7, "armor_class": 15, "dexterity": 14},
    )).json()["id"]
    eid = await _make_encounter(client)
    r = await _add(client, eid, monster_id=mid, initiative=12)
    c = r.json()["combatants"][0]
    assert c["name"] == "Goblin"       # derived from monster
    assert c["max_hp"] == 7
    assert c["armor_class"] == 15
    assert c["dex_modifier"] == 2       # (14-10)//2
    assert c["monster_id"] == mid


async def test_add_combatant_bad_monster(client: AsyncClient):
    eid = await _make_encounter(client)
    r = await _add(client, eid, monster_id=9999, initiative=5)
    assert r.status_code == 404


async def test_initiative_sort_order(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="Low", initiative=8)
    await _add(client, eid, name="High", initiative=20)
    await _add(client, eid, name="Mid", initiative=15)
    combatants = (await client.get(f"/api/v1/encounters/{eid}")).json()["combatants"]
    assert [c["name"] for c in combatants] == ["High", "Mid", "Low"]


async def test_initiative_tiebreak_by_dex(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="SlowDex", initiative=15, dex_modifier=1)
    await _add(client, eid, name="FastDex", initiative=15, dex_modifier=4)
    combatants = (await client.get(f"/api/v1/encounters/{eid}")).json()["combatants"]
    assert [c["name"] for c in combatants] == ["FastDex", "SlowDex"]


async def test_unrolled_initiative_sorts_last(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="Rolled", initiative=1)
    await _add(client, eid, name="Unrolled")  # no initiative
    combatants = (await client.get(f"/api/v1/encounters/{eid}")).json()["combatants"]
    assert [c["name"] for c in combatants] == ["Rolled", "Unrolled"]


async def test_start_and_turn_cycle(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="A", initiative=20)
    await _add(client, eid, name="B", initiative=10)

    s = (await client.post(f"/api/v1/encounters/{eid}/start")).json()
    assert s["round"] == 1 and s["current_turn_index"] == 0

    n1 = (await client.post(f"/api/v1/encounters/{eid}/next-turn")).json()
    assert n1["current_turn_index"] == 1 and n1["round"] == 1

    n2 = (await client.post(f"/api/v1/encounters/{eid}/next-turn")).json()
    assert n2["current_turn_index"] == 0 and n2["round"] == 2  # wrap -> new round

    p1 = (await client.post(f"/api/v1/encounters/{eid}/prev-turn")).json()
    assert p1["current_turn_index"] == 1 and p1["round"] == 1  # back across boundary


async def test_prev_turn_clamps_at_start(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="A", initiative=5)
    await client.post(f"/api/v1/encounters/{eid}/start")
    p = (await client.post(f"/api/v1/encounters/{eid}/prev-turn")).json()
    assert p["round"] == 1 and p["current_turn_index"] == 0  # cannot go below round 1


async def test_update_combatant_hp_and_conditions(client: AsyncClient):
    eid = await _make_encounter(client)
    add = await _add(client, eid, name="Goblin", initiative=10, max_hp=7)
    cid = add.json()["combatants"][0]["id"]
    r = await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"current_hp": 2, "conditions": ["prone", "poisoned"]},
    )
    c = r.json()["combatants"][0]
    assert c["current_hp"] == 2
    assert c["conditions"] == ["prone", "poisoned"]


async def test_remove_combatant(client: AsyncClient):
    eid = await _make_encounter(client)
    add = await _add(client, eid, name="X", initiative=1)
    cid = add.json()["combatants"][0]["id"]
    r = await client.delete(f"/api/v1/encounters/{eid}/combatants/{cid}")
    assert r.status_code == 200
    assert r.json()["combatants"] == []


async def test_delete_encounter_cascades(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="X", initiative=1)
    assert (await client.delete(f"/api/v1/encounters/{eid}")).status_code == 204
    assert (await client.get(f"/api/v1/encounters/{eid}")).status_code == 404
