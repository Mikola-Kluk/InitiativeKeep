"""Create database tables from the Tortoise models.

Run at container startup instead of `aerich upgrade`. The aerich migration
files are raw SQL baked for SQLite (they contain `AUTOINCREMENT`, which
PostgreSQL rejects), so they are not portable to the Neon Postgres we deploy
against. Generating the schema straight from the models emits DDL in whatever
dialect the active connection uses, so it works on both SQLite (dev) and
Postgres (prod).

`safe=True` -> `CREATE TABLE IF NOT EXISTS`, so this is safe to run on every
start. It creates *missing* tables but does not ALTER existing ones, so fields
added to a model later are listed in `app/schema_upgrade.py` and added here.
"""

import asyncio

from tortoise import Tortoise

from app.config import settings
from app.schema_upgrade import add_missing_columns


async def main() -> None:
    await Tortoise.init(config=settings.TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    for col in await add_missing_columns(Tortoise.get_connection("default")):
        print(f"init_db: added column {col}")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
