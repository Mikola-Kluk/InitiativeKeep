import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _make_encounter(client: AsyncClient) -> int:
    return (await client.post("/api/v1/encounters/", json={"name": "Undo fight"})).json()["id"]


async def _add(client, eid, **body) -> dict:
    return (await client.post(f"/api/v1/encounters/{eid}/combatants", json=body)).json()


async def _undo(client, eid):
    return await client.post(f"/api/v1/encounters/{eid}/undo")


async def test_nothing_to_undo_is_409(client):
    eid = await _make_encounter(client)
    data = (await client.get(f"/api/v1/encounters/{eid}")).json()
    assert data["undo_label"] is None
    assert (await _undo(client, eid)).status_code == 409


async def test_undo_missing_encounter_is_404(client):
    assert (await _undo(client, 999999)).status_code == 404


async def test_undo_hp_change(client):
    eid = await _make_encounter(client)
    cid = (await _add(client, eid, name="Goblin", max_hp=7, initiative=10))["combatants"][0]["id"]
    r = await client.patch(f"/api/v1/encounters/{eid}/combatants/{cid}", json={"current_hp": 2})
    assert r.json()["undo_label"] == "Goblin: HP 7 → 2"

    r = await _undo(client, eid)
    assert r.status_code == 200
    assert r.json()["combatants"][0]["current_hp"] == 7
    # the next undo reverts the add
    assert r.json()["undo_label"] == "add Goblin"


async def test_noop_patch_adds_no_history(client):
    eid = await _make_encounter(client)
    cid = (await _add(client, eid, name="Goblin", max_hp=7))["combatants"][0]["id"]
    r = await client.patch(f"/api/v1/encounters/{eid}/combatants/{cid}", json={"current_hp": 7})
    assert r.json()["undo_label"] == "add Goblin"


async def test_undo_conditions_label_and_restore(client):
    eid = await _make_encounter(client)
    cid = (await _add(client, eid, name="Orc", max_hp=15))["combatants"][0]["id"]
    r = await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"conditions": [{"name": "prone", "rounds": None}]},
    )
    assert r.json()["undo_label"] == "Orc: +prone"
    r = await _undo(client, eid)
    assert r.json()["combatants"][0]["conditions"] == []


async def test_undo_turns_and_condition_tick(client):
    eid = await _make_encounter(client)
    await _add(client, eid, name="A", initiative=20, max_hp=5)
    data = await _add(client, eid, name="B", initiative=10, max_hp=5)
    b = data["combatants"][1]["id"]
    await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{b}",
        json={"conditions": [{"name": "stunned", "rounds": 1}]},
    )
    await client.post(f"/api/v1/encounters/{eid}/start")
    await client.post(f"/api/v1/encounters/{eid}/next-turn")
    r = await client.post(f"/api/v1/encounters/{eid}/next-turn")  # wraps: round 2, stunned expires
    assert r.json()["round"] == 2
    assert r.json()["combatants"][1]["conditions"] == []

    r = await _undo(client, eid)
    data = r.json()
    assert data["round"] == 1
    assert data["current_turn_index"] == 1
    assert data["combatants"][1]["conditions"] == [{"name": "stunned", "rounds": 1}]


async def test_undo_start_clears_rolled_initiative(client):
    eid = await _make_encounter(client)
    await _add(client, eid, name="Goblin", max_hp=7)
    r = await client.post(f"/api/v1/encounters/{eid}/start")
    assert r.json()["combatants"][0]["initiative"] is not None
    r = await _undo(client, eid)
    assert r.json()["current_turn_index"] == -1
    assert r.json()["combatants"][0]["initiative"] is None


async def test_undo_remove_restores_same_combatant(client):
    mid = (await client.post(
        "/api/v1/monsters/", json={"name": "Wolf", "hit_points": 11, "legendary_actions": []}
    )).json()["id"]
    eid = await _make_encounter(client)
    data = await _add(client, eid, monster_id=mid, initiative=12)
    wolf = data["combatants"][0]
    await client.patch(f"/api/v1/encounters/{eid}/combatants/{wolf['id']}", json={"current_hp": 4})

    r = await client.delete(f"/api/v1/encounters/{eid}/combatants/{wolf['id']}")
    assert r.json()["combatants"] == []
    assert r.json()["undo_label"] == "remove Wolf"

    restored = (await _undo(client, eid)).json()["combatants"][0]
    assert restored["id"] == wolf["id"]
    assert restored["monster_id"] == mid
    assert restored["current_hp"] == 4


async def test_undo_add_count_removes_all_copies(client):
    eid = await _make_encounter(client)
    await _add(client, eid, name="Goblin", max_hp=7)
    r = await client.post(
        f"/api/v1/encounters/{eid}/combatants", json={"name": "Goblin", "max_hp": 7, "count": 2}
    )
    assert len(r.json()["combatants"]) == 3
    assert r.json()["undo_label"] == "add Goblin ×2"
    r = await _undo(client, eid)
    names = [c["name"] for c in r.json()["combatants"]]
    # back to the lone, un-numbered goblin
    assert names == ["Goblin"]


async def test_history_is_capped(client):
    from app.models.encounter import EncounterSnapshot
    from app.services.encounter import UNDO_LIMIT

    eid = await _make_encounter(client)
    cid = (await _add(client, eid, name="Ogre", max_hp=100))["combatants"][0]["id"]
    for hp in range(UNDO_LIMIT + 5):
        await client.patch(f"/api/v1/encounters/{eid}/combatants/{cid}", json={"current_hp": hp})
    assert await EncounterSnapshot.filter(encounter_id=eid).count() == UNDO_LIMIT


async def test_recharge_used_label_reset_on_start_and_undo(client):
    eid = await _make_encounter(client)
    cid = (await _add(client, eid, name="Dragon", max_hp=200, initiative=15))["combatants"][0]["id"]
    url = f"/api/v1/encounters/{eid}/combatants/{cid}"

    r = await client.patch(url, json={"recharge_used": [{"name": "Fire Breath", "round": 2}]})
    data = r.json()
    assert data["combatants"][0]["recharge_used"] == [{"name": "Fire Breath", "round": 2}]
    assert data["undo_label"] == "Dragon: Fire Breath used"

    r = await client.patch(url, json={"recharge_used": []})
    assert r.json()["undo_label"] == "Dragon: Fire Breath recharged"
    r = await _undo(client, eid)
    assert r.json()["combatants"][0]["recharge_used"] == [{"name": "Fire Breath", "round": 2}]

    r = await client.post(f"/api/v1/encounters/{eid}/start")
    assert r.json()["combatants"][0]["recharge_used"] == []


async def test_recharge_used_is_normalized(client):
    eid = await _make_encounter(client)
    cid = (await _add(client, eid, name="Dragon", max_hp=200))["combatants"][0]["id"]
    r = await client.patch(
        f"/api/v1/encounters/{eid}/combatants/{cid}",
        json={"recharge_used": [{"name": "Fire Breath"}, {"name": "Fire Breath", "round": 3}, "junk", {}]},
    )
    assert r.json()["combatants"][0]["recharge_used"] == [{"name": "Fire Breath", "round": 1}]
