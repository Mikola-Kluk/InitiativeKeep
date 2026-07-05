"""Create database tables from the Tortoise models.

Run at container startup instead of `aerich upgrade`. The aerich migration
files are raw SQL baked for SQLite (they contain `AUTOINCREMENT`, which
PostgreSQL rejects), so they are not portable to the Neon Postgres we deploy
against. Generating the schema straight from the models emits DDL in whatever
dialect the active connection uses, so it works on both SQLite (dev) and
Postgres (prod).

`safe=True` -> `CREATE TABLE IF NOT EXISTS`, so this is safe to run on every
start. Note: it creates *missing* tables but does not ALTER existing ones to
add new columns; on a schema change against a non-empty DB, handle that
separately.
"""

import asyncio

from tortoise import Tortoise

from app.config import settings


async def main() -> None:
    await Tortoise.init(config=settings.TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
