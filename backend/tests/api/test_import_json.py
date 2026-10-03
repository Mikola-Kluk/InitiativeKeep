import pytest

pytestmark = pytest.mark.anyio


async def test_import_native_json(client):
    payload = {
        "name": "Paste Goblin",
        "armor_class": 15,
        "hit_points": 7,
        "dexterity": 14,
        "traits": [{"name": "Nimble", "desc": "Disengages as a bonus action."}],
    }
    resp = await client.post("/api/v1/monsters/import-json", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Paste Goblin"
    assert body["is_homebrew"] is True
    assert body["source"] == "homebrew"
    assert body["armor_class"] == 15
    assert body["dex_modifier"] == 2
    assert body["traits"][0]["name"] == "Nimble"


async def test_import_open5e_shape_maps_special_abilities(client):
    # Open5e uses `special_abilities` for traits and carries extra keys we ignore.
    payload = {
        "name": "SRD Orc",
        "slug": "orc",
        "document__slug": "wotc-srd",
        "armor_class": 13,
        "hit_points": 15,
        "special_abilities": [{"name": "Aggressive", "desc": "Move toward a foe."}],
    }
    resp = await client.post("/api/v1/monsters/import-json", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    # stored as homebrew, not open5e, even though the source JSON was Open5e-shaped
    assert body["is_homebrew"] is True
    assert body["traits"][0]["name"] == "Aggressive"


async def test_import_missing_name_is_422(client):
    resp = await client.post("/api/v1/monsters/import-json", json={"armor_class": 12})
    assert resp.status_code == 422


async def test_import_non_object_is_422(client):
    resp = await client.post("/api/v1/monsters/import-json", json=[1, 2, 3])
    assert resp.status_code == 422


async def test_bulk_import_list(client):
    payload = [
        {"name": "Bulk Goblin", "armor_class": 15, "hit_points": 7},
        {"name": "Bulk Orc", "special_abilities": [{"name": "Aggressive", "desc": "..."}]},
    ]
    resp = await client.post("/api/v1/monsters/import-json/bulk", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert [m["name"] for m in body["imported"]] == ["Bulk Goblin", "Bulk Orc"]
    assert all(m["is_homebrew"] for m in body["imported"])
    assert body["imported"][1]["traits"][0]["name"] == "Aggressive"
    assert body["failed"] == []

    listed = await client.get("/api/v1/monsters/", params={"search": "Bulk"})
    assert len(listed.json()) == 2


async def test_bulk_import_open5e_results_wrapper(client):
    payload = {"count": 1, "results": [{"name": "Wrapped Wolf", "slug": "wolf"}]}
    resp = await client.post("/api/v1/monsters/import-json/bulk", json=payload)
    assert resp.status_code == 200
    assert resp.json()["imported"][0]["name"] == "Wrapped Wolf"


async def test_bulk_import_partial_failure(client):
    payload = [
        {"name": "Good One"},
        {"armor_class": 12},                    # missing name
        {"name": "Bad Str", "strength": 99},    # out of range
        "not an object",
    ]
    resp = await client.post("/api/v1/monsters/import-json/bulk", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert [m["name"] for m in body["imported"]] == ["Good One"]
    failed = body["failed"]
    assert [f["index"] for f in failed] == [1, 2, 3]
    assert failed[1]["name"] == "Bad Str"
    assert "strength" in failed[1]["error"]


@pytest.mark.parametrize("payload", [[], {"foo": "bar"}, {"results": "nope"}])
async def test_bulk_import_bad_shape_is_422(client, payload):
    resp = await client.post("/api/v1/monsters/import-json/bulk", json=payload)
    assert resp.status_code == 422


async def test_bulk_import_over_limit_is_422(client):
    payload = [{"name": f"M{i}"} for i in range(501)]
    resp = await client.post("/api/v1/monsters/import-json/bulk", json=payload)
    assert resp.status_code == 422


async def test_import_identical_statblock_is_not_added_twice(client):
    goblin = {"name": "Twice Goblin", "hit_points": 7, "actions": [{"name": "Scimitar", "desc": "..."}]}
    first = await client.post("/api/v1/monsters/import-json", json=goblin)
    assert first.status_code == 201

    # same stats, name in another letter case -> the existing one comes back
    again = await client.post("/api/v1/monsters/import-json", json={**goblin, "name": "twice goblin"})
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]

    # same name, different stats -> a real second statblock
    other = await client.post("/api/v1/monsters/import-json", json={**goblin, "hit_points": 21})
    assert other.status_code == 201
    assert other.json()["id"] != first.json()["id"]

    assert len((await client.get("/api/v1/monsters/", params={"search": "twice goblin"})).json()) == 2


async def test_bulk_import_skips_statblocks_already_in_library(client):
    wolf = {"name": "Skip Wolf", "hit_points": 11}
    await client.post("/api/v1/monsters/import-json", json=wolf)

    resp = await client.post("/api/v1/monsters/import-json/bulk", json=[
        wolf,                                   # already in the library
        {"name": "Skip Bear", "hit_points": 34},
        {"name": "Skip Bear", "hit_points": 34},  # repeated inside the same paste
    ])

    assert resp.status_code == 200
    body = resp.json()
    assert [m["name"] for m in body["imported"]] == ["Skip Bear"]
    assert [m["name"] for m in body["skipped"]] == ["Skip Wolf", "Skip Bear"]
    assert body["failed"] == []
