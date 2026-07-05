from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "monsters" ADD "damage_resistances" TEXT;
        ALTER TABLE "monsters" ADD "senses" TEXT;
        ALTER TABLE "monsters" ADD "damage_vulnerabilities" TEXT;
        ALTER TABLE "monsters" ADD "languages" TEXT;
        ALTER TABLE "monsters" ADD "damage_immunities" TEXT;
        ALTER TABLE "monsters" ADD "condition_immunities" TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "monsters" DROP COLUMN "damage_resistances";
        ALTER TABLE "monsters" DROP COLUMN "senses";
        ALTER TABLE "monsters" DROP COLUMN "damage_vulnerabilities";
        ALTER TABLE "monsters" DROP COLUMN "languages";
        ALTER TABLE "monsters" DROP COLUMN "damage_immunities";
        ALTER TABLE "monsters" DROP COLUMN "condition_immunities";"""


MODELS_STATE = (
    "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"
)
