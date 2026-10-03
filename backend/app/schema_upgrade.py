"""Add columns introduced after launch to databases that already have the table.

`Tortoise.generate_schemas(safe=True)` creates missing tables but never ALTERs
existing ones, so a new model field would be missing on the live Neon DB. Each
entry below is added with `ALTER TABLE ... ADD COLUMN` only if it isn't there
yet, so this is safe to run on every start (see init_db.py). Works on SQLite
(dev) and PostgreSQL (prod).
"""

from tortoise import BaseDBAsyncClient

# (table, column, {dialect: column definition})
ADDED_COLUMNS: list[tuple[str, str, dict[str, str]]] = [
    ("combatants", "recharge_used", {
        "sqlite": "JSON NOT NULL DEFAULT '[]'",
        "postgres": "JSONB NOT NULL DEFAULT '[]'::jsonb",
    }),
    ("combatants", "nick", {
        "sqlite": "VARCHAR(100)",
        "postgres": "VARCHAR(100)",
    }),
]


async def _existing_columns(conn: BaseDBAsyncClient, table: str) -> set[str]:
    if conn.capabilities.dialect == "sqlite":
        rows = await conn.execute_query_dict(f"PRAGMA table_info({table})")
        return {r["name"] for r in rows}
    rows = await conn.execute_query_dict(
        "SELECT column_name FROM information_schema.columns WHERE table_name = $1", [table]
    )
    return {r["column_name"] for r in rows}


async def add_missing_columns(
    conn: BaseDBAsyncClient, columns: list[tuple[str, str, dict[str, str]]] = ADDED_COLUMNS
) -> list[str]:
    """Add any listed column the table lacks. Returns "table.column" for each one added."""
    added = []
    dialect = conn.capabilities.dialect
    for table, column, ddl in columns:
        if column in await _existing_columns(conn, table):
            continue
        await conn.execute_script(f"ALTER TABLE {table} ADD COLUMN {column} {ddl[dialect]}")
        added.append(f"{table}.{column}")
    return added
