import pytest

from app.models.monster import Monster

pytestmark = pytest.mark.anyio

API = "/api/v1/encounters"


async def _prepare(client, enemies) -> dict:
    resp = await client.post(f"{API}/prepare", json={"name": "Siege", "enemies": enemies})
    assert resp.status_code == 201
    return resp.json()


def _names(enc: dict, *, active: bool) -> list[str]:
    return [c["name"] for c in enc["combatants"] if (c["wave"] <= enc["current_wave"]) == active]


async def test_everything_is_wave_zero_by_default(client):
    goblin = await Monster.create(name="Goblin")
    enc = (await client.post(f"{API}/", json={"name": "Plain"})).json()
    assert enc["current_wave"] == 0
    enc = (await client.post(f"{API}/{enc['id']}/combatants", json={"monster_id": goblin.id})).json()
    assert enc["combatants"][0]["wave"] == 0


async def test_prepare_puts_enemies_in_waves(client):
    await Monster.create(name="Goblin")
    await Monster.create(name="Ogre")
    enc = await _prepare(client, [
        {"monster": "Ogre", "wave": 2},
        {"monster": "Goblin", "count": 2},
        {"monster": "Goblin", "wave": 1},
    ])
    assert enc["current_wave"] == 0
    # in the fight first, then the reserve by wave
    assert [(c["name"], c["wave"]) for c in enc["combatants"]] == [
        ("Goblin (1)", 0), ("Goblin (2)", 0), ("Goblin (3)", 1), ("Ogre", 2),
    ]


async def test_start_leaves_the_reserve_alone(client):
    await Monster.create(name="Goblin", hit_dice="2d6")
    enc = await _prepare(client, [{"monster": "Goblin"}, {"monster": "Goblin", "wave": 1}])

    enc = (await client.post(f"{API}/{enc['id']}/start")).json()

    first, waiting = enc["combatants"]
    assert (first["wave"], waiting["wave"]) == (0, 1)
    assert first["initiative"] is not None
    assert waiting["initiative"] is None
    assert enc["current_turn_index"] == 0


async def test_turns_skip_the_reserve(client):
    await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin", "count": 2}, {"monster": "Goblin", "count": 3, "wave": 1}])
    eid = enc["id"]
    await client.post(f"{API}/{eid}/start")

    enc = (await client.post(f"{API}/{eid}/next-turn")).json()
    assert (enc["round"], enc["current_turn_index"]) == (1, 1)
    enc = (await client.post(f"{API}/{eid}/next-turn")).json()
    assert (enc["round"], enc["current_turn_index"]) == (2, 0)  # wrapped after 2, not 5
    enc = (await client.post(f"{API}/{eid}/prev-turn")).json()
    assert (enc["round"], enc["current_turn_index"]) == (1, 1)


async def test_next_wave_needs_a_running_fight_and_a_waiting_wave(client):
    await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin"}, {"monster": "Goblin", "wave": 1}])
    eid = enc["id"]

    not_started = await client.post(f"{API}/{eid}/next-wave")
    assert not_started.status_code == 409

    await client.post(f"{API}/{eid}/start")
    assert (await client.post(f"{API}/{eid}/next-wave")).status_code == 200
    nothing_left = await client.post(f"{API}/{eid}/next-wave")
    assert nothing_left.status_code == 409

    assert (await client.post(f"{API}/999999/next-wave")).status_code == 404


async def test_next_wave_joins_and_keeps_the_turn(client):
    ogre = await Monster.create(name="Ogre", hit_dice="7d10+21")
    enc = (await client.post(f"{API}/", json={"name": "Gate"})).json()
    eid = enc["id"]
    await client.post(f"{API}/{eid}/combatants", json={"name": "Aria", "is_pc": True, "initiative": 10})
    await client.post(f"{API}/{eid}/combatants", json={"name": "Borin", "is_pc": True, "initiative": 5})
    # the ogre's initiative is set, so it lands above both players when it joins
    await client.post(f"{API}/{eid}/combatants", json={"monster_id": ogre.id, "wave": 1, "initiative": 20})
    await client.post(f"{API}/{eid}/start")
    enc = (await client.post(f"{API}/{eid}/next-turn")).json()
    assert enc["combatants"][enc["current_turn_index"]]["name"] == "Borin"

    enc = (await client.post(f"{API}/{eid}/next-wave")).json()

    assert enc["current_wave"] == 1
    assert _names(enc, active=True) == ["Ogre", "Aria", "Borin"]
    assert _names(enc, active=False) == []
    assert enc["combatants"][enc["current_turn_index"]]["name"] == "Borin"
    assert enc["round"] == 1
    assert enc["undo_label"] == "start wave 1"
    ogre = enc["combatants"][0]
    assert ogre["initiative"] == 20           # kept
    assert 28 <= ogre["max_hp"] <= 91         # rolled from 7d10+21
    assert ogre["current_hp"] == ogre["max_hp"]

    # the wave now takes turns: Borin -> round 2, Ogre
    enc = (await client.post(f"{API}/{eid}/next-turn")).json()
    assert (enc["round"], enc["combatants"][enc["current_turn_index"]]["name"]) == (2, "Ogre")


async def test_undo_sends_the_wave_back(client):
    await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin"}, {"monster": "Goblin", "wave": 1}])
    eid = enc["id"]
    await client.post(f"{API}/{eid}/start")
    await client.post(f"{API}/{eid}/next-wave")

    enc = (await client.post(f"{API}/{eid}/undo")).json()

    assert enc["current_wave"] == 0
    assert _names(enc, active=False) == ["Goblin (2)"]
    assert enc["combatants"][1]["initiative"] is None
    assert enc["current_turn_index"] == 0


async def test_wave_numbers_may_have_gaps(client):
    await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin"}, {"monster": "Goblin", "wave": 3}])
    eid = enc["id"]
    await client.post(f"{API}/{eid}/start")
    enc = (await client.post(f"{API}/{eid}/next-wave")).json()
    assert enc["current_wave"] == 3
    assert _names(enc, active=False) == []


async def test_new_combatant_joins_the_current_wave_unless_told_otherwise(client):
    goblin = await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin"}, {"monster": "Goblin", "wave": 1}])
    eid = enc["id"]
    await client.post(f"{API}/{eid}/start")
    await client.post(f"{API}/{eid}/next-wave")

    enc = (await client.post(f"{API}/{eid}/combatants", json={"monster_id": goblin.id})).json()
    assert {c["name"]: c["wave"] for c in enc["combatants"]}["Goblin (3)"] == 1

    enc = (await client.post(f"{API}/{eid}/combatants", json={"monster_id": goblin.id, "wave": 2})).json()
    assert _names(enc, active=False) == ["Goblin (4)"]


async def test_move_combatant_to_another_wave(client):
    await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin", "count": 2}])
    eid, cid = enc["id"], enc["combatants"][1]["id"]

    enc = (await client.patch(f"{API}/{eid}/combatants/{cid}", json={"wave": 1})).json()

    assert _names(enc, active=False) == ["Goblin (2)"]
    assert enc["undo_label"] == "Goblin (2): wave 0 → 1"


async def test_restart_begins_again_from_wave_zero(client):
    await Monster.create(name="Goblin")
    enc = await _prepare(client, [{"monster": "Goblin"}, {"monster": "Goblin", "wave": 1}])
    eid = enc["id"]
    await client.post(f"{API}/{eid}/start")
    await client.post(f"{API}/{eid}/next-wave")
    await client.post(f"{API}/{eid}/end")

    enc = (await client.post(f"{API}/{eid}/start")).json()

    assert enc["current_wave"] == 0
    assert _names(enc, active=False) == ["Goblin (2)"]


async def test_prepare_rejects_bad_wave(client):
    await Monster.create(name="Goblin")
    resp = await client.post(f"{API}/prepare", json={"name": "Bad", "enemies": [{"monster": "Goblin", "wave": -1}]})
    assert resp.status_code == 422
