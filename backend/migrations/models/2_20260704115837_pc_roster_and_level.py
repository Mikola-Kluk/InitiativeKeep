from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "characters" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "max_hp" INT NOT NULL DEFAULT 1,
    "level" INT NOT NULL DEFAULT 1,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) /* A saved player character (party roster). Reusable across encounters — */;
        ALTER TABLE "combatants" ADD "level" INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "combatants" DROP COLUMN "level";
        DROP TABLE IF EXISTS "characters";"""


MODELS_STATE = (
    "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"
    "Q="
)
