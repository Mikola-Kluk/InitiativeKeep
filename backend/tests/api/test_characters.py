import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_list_characters_empty(client: AsyncClient):
    r = await client.get("/api/v1/characters/")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_character_defaults(client: AsyncClient):
    r = await client.post("/api/v1/characters/", json={"name": "Bilbo"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Bilbo"
    assert data["max_hp"] == 1   # schema default
    assert data["level"] == 1


async def test_create_character_full(client: AsyncClient):
    r = await client.post(
        "/api/v1/characters/", json={"name": "Gandalf", "max_hp": 60, "level": 20}
    )
    data = r.json()
    assert data["max_hp"] == 60
    assert data["level"] == 20


@pytest.mark.parametrize("bad", [{"level": 21}, {"level": 0}, {"max_hp": 0}])
async def test_create_character_validation(client: AsyncClient, bad):
    r = await client.post("/api/v1/characters/", json={"name": "X", **bad})
    assert r.status_code == 422


async def test_update_character(client: AsyncClient):
    cid = (await client.post(
        "/api/v1/characters/", json={"name": "Frodo", "level": 3}
    )).json()["id"]
    r = await client.patch(f"/api/v1/characters/{cid}", json={"level": 4})
    assert r.status_code == 200
    assert r.json()["level"] == 4
    assert r.json()["name"] == "Frodo"  # untouched


async def test_update_character_not_found(client: AsyncClient):
    r = await client.patch("/api/v1/characters/9999", json={"level": 5})
    assert r.status_code == 404


async def test_delete_character(client: AsyncClient):
    cid = (await client.post("/api/v1/characters/", json={"name": "Tmp"})).json()["id"]
    assert (await client.delete(f"/api/v1/characters/{cid}")).status_code == 204
    # gone from the roster
    assert (await client.get("/api/v1/characters/")).json() == []


async def test_delete_character_not_found(client: AsyncClient):
    assert (await client.delete("/api/v1/characters/9999")).status_code == 404
