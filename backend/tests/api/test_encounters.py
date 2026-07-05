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


async def test_duplicate_combatants_get_numbered(client: AsyncClient):
    mid = (await client.post("/api/v1/monsters/", json={"name": "Goblin"})).json()["id"]
    eid = await _make_encounter(client)

    r1 = await _add(client, eid, monster_id=mid)
    assert [c["name"] for c in r1.json()["combatants"]] == ["Goblin"]  # lone -> plain

    r2 = await _add(client, eid, monster_id=mid)  # second -> pair numbered
    names2 = sorted(c["name"] for c in r2.json()["combatants"])
    assert names2 == ["Goblin (1)", "Goblin (2)"]

    r3 = await _add(client, eid, monster_id=mid)
    names3 = sorted(c["name"] for c in r3.json()["combatants"])
    assert names3 == ["Goblin (1)", "Goblin (2)", "Goblin (3)"]


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
    # PCs keep their entered initiative (NPC initiative is rerolled on start)
    await _add(client, eid, name="A", is_pc=True, initiative=20)
    await _add(client, eid, name="B", is_pc=True, initiative=10)

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
    await _add(client, eid, name="A", is_pc=True, initiative=5)
    await client.post(f"/api/v1/encounters/{eid}/start")
    p = (await client.post(f"/api/v1/encounters/{eid}/prev-turn")).json()
    assert p["round"] == 1 and p["current_turn_index"] == 0  # cannot go below round 1


async def test_start_rolls_npc_initiative_and_hp(client: AsyncClient):
    # monster with a fixed hit_dice -> HP rolled into [2, 12]
    mid = (await client.post(
        "/api/v1/monsters/",
        json={"name": "Goblin", "hit_points": 999, "hit_dice": "2d6", "dexterity": 14},
    )).json()["id"]
    eid = await _make_encounter(client)
    await _add(client, eid, monster_id=mid)  # no initiative provided

    started = (await client.post(f"/api/v1/encounters/{eid}/start")).json()
    c = started["combatants"][0]
    assert c["initiative"] is not None       # NPC initiative was rolled
    assert 1 + 2 <= c["initiative"] <= 20 + 2  # d20 + dex_mod(=2)
    assert 2 <= c["max_hp"] <= 12             # rolled from 2d6, not the 999 default
    assert c["current_hp"] == c["max_hp"]


async def test_start_keeps_pc_initiative(client: AsyncClient):
    eid = await _make_encounter(client)
    await _add(client, eid, name="Hero", is_pc=True, initiative=13, max_hp=30)
    started = (await client.post(f"/api/v1/encounters/{eid}/start")).json()
    c = started["combatants"][0]
    assert c["initiative"] == 13   # unchanged
    assert c["max_hp"] == 30       # unchanged


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
    # plain strings are normalized on read to {"name", "rounds"} objects
    assert c["conditions"] == [
        {"name": "prone", "rounds": None},
        {"name": "poisoned", "rounds": None},
    ]


async def test_timed_condition_ticks_down_each_round(client: AsyncClient):
    eid = await _make_encounter(client)
    add = await _add(client, eid, name="Solo", is_pc=True, initiative=10)
    cid = add.json()["combatants"][0]["id"]
    await client.post(f"/api/v1/encounters/{eid}/start")

    # 2-round timed condition
    await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"conditions": [{"name": "stunned", "rounds": 2}]},
    )
    # one full round (single combatant wraps immediately) -> rounds 2 -> 1
    r = (await client.post(f"/api/v1/encounters/{eid}/next-turn")).json()
    assert r["round"] == 2
    assert r["combatants"][0]["conditions"] == [{"name": "stunned", "rounds": 1}]

    # another round -> expires and drops off
    r = (await client.post(f"/api/v1/encounters/{eid}/next-turn")).json()
    assert r["round"] == 3
    assert r["combatants"][0]["conditions"] == []


async def test_permanent_condition_never_ticks(client: AsyncClient):
    eid = await _make_encounter(client)
    add = await _add(client, eid, name="Solo", is_pc=True, initiative=10)
    cid = add.json()["combatants"][0]["id"]
    await client.post(f"/api/v1/encounters/{eid}/start")
    await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"conditions": [{"name": "prone", "rounds": None}]},
    )
    r = (await client.post(f"/api/v1/encounters/{eid}/next-turn")).json()
    assert r["combatants"][0]["conditions"] == [{"name": "prone", "rounds": None}]


async def test_legendary_actions_spawn_and_refill(client: AsyncClient):
    mid = (await client.post(
        "/api/v1/monsters/",
        json={"name": "Lich", "legendary_actions": [{"name": "Cantrip"}]},
    )).json()["id"]
    eid = await _make_encounter(client)
    add = await _add(client, eid, monster_id=mid, initiative=10)
    cid = add.json()["combatants"][0]["id"]
    # spawned from a monster with legendary_actions -> pool of 3
    assert add.json()["combatants"][0]["legendary_actions_max"] == 3
    assert add.json()["combatants"][0]["legendary_actions_remaining"] == 3

    await client.post(f"/api/v1/encounters/{eid}/start")
    # spend two
    await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"legendary_actions_remaining": 1},
    )
    # advancing back to the creature's own turn refills the pool
    r = (await client.post(f"/api/v1/encounters/{eid}/next-turn")).json()
    assert r["combatants"][0]["legendary_actions_remaining"] == 3


async def test_concentration_toggle(client: AsyncClient):
    eid = await _make_encounter(client)
    add = await _add(client, eid, name="Wizard", is_pc=True, initiative=10)
    cid = add.json()["combatants"][0]["id"]
    assert add.json()["combatants"][0]["concentrating"] is False
    r = await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"concentrating": True},
    )
    assert r.json()["combatants"][0]["concentrating"] is True


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
