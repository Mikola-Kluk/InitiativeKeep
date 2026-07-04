from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "monsters" ADD "legendary_desc" TEXT;
        ALTER TABLE "monsters" ADD "reactions" JSON NOT NULL;
        ALTER TABLE "monsters" ADD "legendary_actions" JSON NOT NULL;
        ALTER TABLE "combatants" ADD "concentrating" INT NOT NULL DEFAULT 0;
        ALTER TABLE "combatants" ADD "legendary_actions_remaining" INT NOT NULL DEFAULT 0;
        ALTER TABLE "combatants" ADD "legendary_actions_max" INT NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "monsters" DROP COLUMN "legendary_desc";
        ALTER TABLE "monsters" DROP COLUMN "reactions";
        ALTER TABLE "monsters" DROP COLUMN "legendary_actions";
        ALTER TABLE "combatants" DROP COLUMN "concentrating";
        ALTER TABLE "combatants" DROP COLUMN "legendary_actions_remaining";
        ALTER TABLE "combatants" DROP COLUMN "legendary_actions_max";"""


MODELS_STATE = (
    "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"
    "HQqWeMSu/8Hy8D/kNMsU"
)
