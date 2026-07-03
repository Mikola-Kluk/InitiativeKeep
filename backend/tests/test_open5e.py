import httpx
import pytest

from app.services import open5e as svc

pytestmark = pytest.mark.anyio


_GOBLIN = {
    "slug": "goblin",
    "name": "Goblin",
    "size": "Small",
    "type": "humanoid",
    "alignment": "neutral evil",
    "armor_class": 15,
    "armor_desc": "leather armor, shield",
    "hit_points": 7,
    "hit_dice": "2d6",
    "speed": {"walk": 30},
    "strength": 8,
    "dexterity": 14,
    "constitution": 10,
    "intelligence": 10,
    "wisdom": 8,
    "charisma": 8,
    "challenge_rating": "1/4",
    "cr": 0.25,
    "special_abilities": [{"name": "Nimble Escape", "desc": "..."}],
    "actions": [{"name": "Scimitar", "desc": "..."}],
}


class _FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)


def _fake_client_factory(resp: _FakeResp):
    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return resp

    return _FakeClient


async def test_map_open5e_to_fields():
    fields = svc._map_open5e_to_fields(_GOBLIN)
    assert fields["source"] == "open5e"
    assert fields["is_homebrew"] is False
    assert fields["hit_points"] == 7
    assert fields["cr"] == 0.25
    assert fields["traits"] == _GOBLIN["special_abilities"]  # renamed field
    assert fields["actions"] == _GOBLIN["actions"]


async def test_map_open5e_missing_fields_fallback():
    fields = svc._map_open5e_to_fields({"slug": "x", "name": "X"})
    assert fields["armor_class"] == 10
    assert fields["hit_points"] == 1
    assert fields["dexterity"] == 10
    assert fields["speed"] == {}
    assert fields["traits"] == []


async def test_browse_open5e(monkeypatch):
    resp = _FakeResp({"count": 1, "results": [{**_GOBLIN, "document__slug": "tob"}]})
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    out = await svc.browse_open5e(query="goblin")
    assert out["count"] == 1
    assert out["page"] == 1
    assert out["num_pages"] == 1
    assert out["results"] == [
        {"slug": "goblin", "name": "Goblin", "type": "humanoid",
         "challenge_rating": "1/4", "cr": 0.25, "hit_points": 7, "document": "tob"}
    ]


async def test_browse_pagination_num_pages(monkeypatch):
    resp = _FakeResp({"count": 120, "results": []})
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    out = await svc.browse_open5e(page=2)
    assert out["count"] == 120
    assert out["page"] == 2
    assert out["num_pages"] == 3  # ceil(120/50)


async def test_preview_open5e(monkeypatch):
    resp = _FakeResp(_GOBLIN)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    p = await svc.preview_open5e("goblin")
    assert p is not None
    assert p["id"] == 0                 # not persisted
    assert p["name"] == "Goblin"
    assert p["dex_modifier"] == 2       # (14-10)//2
    assert p["actions"] == _GOBLIN["actions"]


async def test_preview_open5e_404(monkeypatch):
    resp = _FakeResp(None, status_code=404)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    assert await svc.preview_open5e("nope") is None


async def test_import_monster_creates(monkeypatch):
    resp = _FakeResp(_GOBLIN)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    m = await svc.import_monster("goblin")
    assert m is not None
    assert m.slug == "goblin"
    assert m.source == "open5e"
    assert m.hit_points == 7


async def test_import_monster_idempotent(monkeypatch):
    resp = _FakeResp(_GOBLIN)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    first = await svc.import_monster("goblin")

    # second import must return existing without touching network
    def _boom(*a, **kw):
        raise AssertionError("should not call network on re-import")

    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    second = await svc.import_monster("goblin")
    assert second.id == first.id


async def test_import_monster_404(monkeypatch):
    resp = _FakeResp(None, status_code=404)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    assert await svc.import_monster("nonexistent") is None


async def test_import_many(monkeypatch):
    resp = _FakeResp(_GOBLIN)  # every fetch returns goblin payload
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    # goblin imports; the model has a unique-ish slug so re-listing same slug
    # twice still lands in imported (idempotent create returns existing)
    out = await svc.import_many(["goblin", "goblin"])
    assert out["imported"] == ["goblin", "goblin"]
    assert out["failed"] == []


async def test_import_many_handles_404(monkeypatch):
    resp = _FakeResp(None, status_code=404)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_factory(resp))
    out = await svc.import_many(["ghost"])
    assert out["imported"] == []
    assert out["failed"] == ["ghost"]
