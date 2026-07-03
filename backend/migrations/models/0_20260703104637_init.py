from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "monsters" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "slug" VARCHAR(255),
    "source" VARCHAR(100) NOT NULL DEFAULT 'homebrew',
    "is_homebrew" INT NOT NULL DEFAULT 1,
    "size" VARCHAR(20),
    "type" VARCHAR(100),
    "alignment" VARCHAR(100),
    "armor_class" INT NOT NULL DEFAULT 10,
    "armor_desc" VARCHAR(255),
    "hit_points" INT NOT NULL DEFAULT 1,
    "hit_dice" VARCHAR(50),
    "speed" JSON NOT NULL,
    "strength" INT NOT NULL DEFAULT 10,
    "dexterity" INT NOT NULL DEFAULT 10,
    "constitution" INT NOT NULL DEFAULT 10,
    "intelligence" INT NOT NULL DEFAULT 10,
    "wisdom" INT NOT NULL DEFAULT 10,
    "charisma" INT NOT NULL DEFAULT 10,
    "challenge_rating" VARCHAR(10),
    "cr" REAL,
    "traits" JSON NOT NULL,
    "actions" JSON NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) /* A D&D statblock. Either imported from Open5e or homebrew. */;
CREATE TABLE IF NOT EXISTS "encounters" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "notes" TEXT,
    "round" INT NOT NULL DEFAULT 1,
    "current_turn_index" INT NOT NULL DEFAULT -1,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) /* A single combat. Holds ordered combatants and turn\/round state. */;
CREATE TABLE IF NOT EXISTS "combatants" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "is_pc" INT NOT NULL DEFAULT 0,
    "initiative" INT,
    "dex_modifier" INT NOT NULL DEFAULT 0,
    "armor_class" INT NOT NULL DEFAULT 10,
    "max_hp" INT NOT NULL DEFAULT 1,
    "current_hp" INT NOT NULL DEFAULT 1,
    "temp_hp" INT NOT NULL DEFAULT 0,
    "conditions" JSON NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "encounter_id" INT NOT NULL REFERENCES "encounters" ("id") ON DELETE CASCADE,
    "monster_id" INT REFERENCES "monsters" ("id") ON DELETE SET NULL
) /* A participant in an encounter — a PC or a monster instance. */;
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
