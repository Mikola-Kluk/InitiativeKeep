from contextlib import asynccontextmanager

import pytest
from httpx import AsyncClient, ASGITransport
from tortoise import Tortoise

from app.main import app

TEST_DB_URL = "sqlite://:memory:"

_MODELS = ["app.models.monster", "app.models.encounter"]


@asynccontextmanager
async def noop_lifespan(app):
    # skip RegisterTortoise; the init_db fixture manages the test DB
    yield


app.router.lifespan_context = noop_lifespan


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def init_db():
    await Tortoise.init(db_url=TEST_DB_URL, modules={"models": _MODELS})
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture(autouse=True)
async def clean_db(init_db):
    yield
    from app.models.encounter import Combatant, Encounter
    from app.models.monster import Monster

    await Combatant.all().delete()
    await Encounter.all().delete()
    await Monster.all().delete()


@pytest.fixture
async def client(init_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
