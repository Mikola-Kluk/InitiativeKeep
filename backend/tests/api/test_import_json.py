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
