import pytest
from tortoise import Tortoise

from app.schema_upgrade import add_missing_columns

pytestmark = pytest.mark.anyio

_PROBE = [("upgrade_probe", "extra", {"sqlite": "JSON NOT NULL DEFAULT '[]'", "postgres": "unused"})]


async def test_adds_missing_column_once(init_db):
    conn = Tortoise.get_connection("default")
    await conn.execute_script("CREATE TABLE upgrade_probe (id INTEGER PRIMARY KEY)")
    try:
        assert await add_missing_columns(conn, _PROBE) == ["upgrade_probe.extra"]
        assert await add_missing_columns(conn, _PROBE) == []  # idempotent
        await conn.execute_script("INSERT INTO upgrade_probe (id) VALUES (1)")
        rows = await conn.execute_query_dict("SELECT extra FROM upgrade_probe")
        assert rows[0]["extra"] == "[]"
    finally:
        await conn.execute_script("DROP TABLE upgrade_probe")


async def test_current_models_need_nothing(init_db):
    # generate_schemas already created every listed column
    assert await add_missing_columns(Tortoise.get_connection("default")) == []
