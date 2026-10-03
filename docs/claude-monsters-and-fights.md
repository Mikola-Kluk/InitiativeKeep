# InitiativeKeep — instructions for Claude: monsters and fights

Give this file to Claude when you want it to add monsters to the library or prepare a
fight. It covers the JSON shapes the app accepts and the API calls behind them.

## How you deliver the result

Pick the mode from what you have access to:

- **No access to the app (plain chat).** Output JSON in a code block for the user to
  paste. Monsters go into *Monsters → 📋 Paste JSON*; a fight goes into
  *Encounters → 📋 Paste JSON*. Output only valid JSON in the block — no comments, no
  trailing commas.
- **Access to the API (can send HTTP requests).** Call the endpoints below. Base URL is
  `<app origin>/api/v1` (`http://localhost:8000/api/v1` locally; ask the user for the
  deployed origin). There is no authentication. Send `Content-Type: application/json`.

Always do monsters first, then the fight: a fight can only reference monsters that are
already in the library.

## Rules that are easy to get wrong

1. **A fight contains enemies only.** Never put player characters in it. The DM adds
   the players in the tracker afterwards.
2. **Do not roll anything.** No initiative, no HP rolls. The app rolls initiative and
   rerolls monster HP from `hit_dice` when the DM starts combat.
3. **Do not create namesakes.** Pasting a statblock the library already has (same name,
   same stats) is harmless — it is skipped. But a statblock with an existing name and
   *different* stats is added as a second one, and that name then cannot be used in a
   fight (409) until you pick one by `monster_id`. Check the library first; reuse what
   is there, and give a variant its own name ("Goblin Sniper", not "Goblin").
4. **Monster names in a fight must match the library exactly** (letter case and
   surrounding spaces are ignored; partial names do not match). "Goblin" does not find
   "Goblin Boss".
5. **Prefer an Open5e import over writing a statblock by hand** when the creature
   exists there. Write homebrew JSON only for custom creatures.
6. Ability scores must be 1–30, `hit_points` ≥ 1, `armor_class` ≥ 0 for anything you
   write yourself.

## 1. Check what is already in the library

```
GET /monsters/?search=<part of name>
```

Returns a list of statblocks (`id`, `name`, `challenge_rating`, `source`, …). `search`
is a case-insensitive "contains" on the name; omit it to list everything.

Without API access, ask the user which monsters they already have.

## 2. Add monsters

### 2a. Import from Open5e (official and third-party statblocks)

Find the creature:

```
GET /open5e/monsters?q=<name>&cr=<cr>&type=<type>&document=<source slug>&page=<n>
```

All filters are optional. 20 results per page; the response is
`{count, page, num_pages, results: [{slug, name, type, challenge_rating, cr, hit_points, document}]}`.
`GET /open5e/sources` lists the available `document` slugs.

Import by slug:

```
POST /open5e/import/<slug>              → 201, the stored statblock
POST /open5e/import                     body: {"slugs": ["goblin", "wolf"]}
                                        → {"imported": [...slugs], "failed": [...slugs]}
```

Importing the same slug twice is safe — it does not create a second copy.

### 2b. Homebrew statblock as JSON

```
POST /monsters/import-json              body: one statblock object
                                        → 201 added, or 200 = identical one already
                                          in the library (returned, nothing added)
POST /monsters/import-json/bulk         body: a list of statblocks, or
                                        {"monsters": [...]} / {"results": [...]}
                                        → 200 {"imported": [...], "skipped": [...],
                                               "failed": [{index, name, error}]}
```

Bulk takes up to 500 statblocks and saves the valid ones even if others fail — read
`failed` and report or fix those. `skipped` lists statblocks that were already in the
library (same name and stats); that is not an error. A single bad statblock on the non-bulk endpoint
returns 422.

Only `name` is required; everything else falls back to its default. Unknown keys are
ignored.

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | required | |
| `size` | string | — | Tiny, Small, Medium, Large, Huge, Gargantuan |
| `type` | string | — | humanoid, beast, dragon, … |
| `alignment` | string | — | |
| `armor_class` | integer ≥ 0 | 10 | |
| `armor_desc` | string | — | e.g. "natural armor" |
| `hit_points` | integer ≥ 1 | 1 | Average HP |
| `hit_dice` | string | — | `NdM+K`, e.g. `"6d8+12"`. Always include it: HP is rolled from it at combat start. |
| `speed` | object | `{}` | `{"walk": 30, "fly": 60, "swim": 20}` |
| `strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, `charisma` | integer 1–30 | 10 | Dexterity sets the initiative bonus. |
| `challenge_rating` | string | — | Display form: `"1/4"`, `"5"` |
| `cr` | number | — | Numeric form: `0.25`, `5`. Set both `challenge_rating` and `cr`. |
| `damage_vulnerabilities`, `damage_resistances`, `damage_immunities`, `condition_immunities` | string | — | Free text, comma-separated |
| `senses` | string | — | e.g. "darkvision 60 ft., passive Perception 12" |
| `languages` | string | — | |
| `traits` | `[{name, desc}]` | `[]` | Open5e's `special_abilities` is accepted as an alias. |
| `actions` | `[{name, desc}]` | `[]` | |
| `reactions` | `[{name, desc}]` | `[]` | |
| `legendary_desc` | string | — | Intro text for legendary actions |
| `legendary_actions` | `[{name, desc}]` | `[]` | If not empty, the creature gets a pool of 3 legendary actions per round. |

Conventions the tracker relies on:

- **Recharge abilities** — put the recharge in the ability's `name`, exactly like the
  rulebooks: `"Fire Breath (Recharge 5–6)"`, `"Web (Recharge 6)"`,
  `"Howl (Recharges after a Short or Long Rest)"`. The tracker reads it from the name
  and prompts the DM to roll.
- **Legendary creatures** — list the actions in `legendary_actions`; the pool of 3 is
  set up automatically.
- Write `desc` as plain text with the full attack line, e.g.
  `"Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 7 (1d8 + 3) slashing damage."`

Example:

```json
{
  "name": "Ashen Warden",
  "size": "Large",
  "type": "elemental",
  "alignment": "neutral",
  "armor_class": 16,
  "armor_desc": "natural armor",
  "hit_points": 85,
  "hit_dice": "10d10+30",
  "speed": { "walk": 30 },
  "strength": 18,
  "dexterity": 12,
  "constitution": 16,
  "intelligence": 8,
  "wisdom": 12,
  "charisma": 8,
  "challenge_rating": "5",
  "cr": 5,
  "damage_immunities": "fire, poison",
  "condition_immunities": "poisoned",
  "senses": "darkvision 60 ft., passive Perception 11",
  "languages": "Ignan",
  "traits": [
    { "name": "Heated Body", "desc": "A creature that touches the warden or hits it with a melee attack while within 5 feet takes 5 (1d10) fire damage." }
  ],
  "actions": [
    { "name": "Multiattack", "desc": "The warden makes two Slam attacks." },
    { "name": "Slam", "desc": "Melee Weapon Attack: +7 to hit, reach 5 ft., one target. Hit: 13 (2d8 + 4) bludgeoning damage plus 5 (1d10) fire damage." },
    { "name": "Cinder Burst (Recharge 5–6)", "desc": "Each creature within 15 feet must make a DC 14 Dexterity saving throw, taking 21 (6d6) fire damage on a failed save, or half as much on a successful one." }
  ],
  "reactions": [],
  "legendary_actions": []
}
```

## 3. Prepare a fight

```
POST /encounters/prepare                → 201, the new encounter
```

```json
{
  "name": "Ambush at the ford",
  "notes": "Goblins hide under the bridge; the boss arrives in round 3.",
  "enemies": [
    { "monster": "Goblin", "count": 4 },
    { "monster": "Bandit", "nick": "elf, carries the key" },
    { "monster": "Goblin Boss", "name": "Skarr" },
    { "monster_id": 17, "count": 2 },
    { "monster": "Wolf", "count": 3, "wave": 1 },
    { "monster": "Ogre", "wave": 2 }
  ]
}
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | required | Encounter name |
| `notes` | string | — | Free text for the DM |
| `enemies` | list | `[]` | Up to 50 entries |
| `enemies[].monster` | string | one of the two | Library name of the statblock |
| `enemies[].monster_id` | integer | one of the two | Library id; use it when two statblocks share a name |
| `enemies[].count` | integer 1–20 | 1 | Copies; they are numbered automatically: "Goblin (1)", "Goblin (2)", … |
| `enemies[].name` | string | — | Display name replacing the statblock name (for a named NPC) |
| `enemies[].wave` | integer 0–50 | 0 | When the creature arrives. 0 = in the fight from the start; 1, 2, … = reinforcements that wait in reserve until the DM starts that wave. |
| `enemies[].nick` | string ≤ 100 | — | Short tag shown beside the name ("elf", "archer", "Skarr"); the name itself stays. Applied to every copy of the entry. |

Each enemy needs exactly one of `monster` / `monster_id`. Don't number copies yourself —
use `count`.

`name` vs `nick`: use `name` when the creature *is* someone ("Skarr" instead of "Goblin
Boss"); use `nick` to tell otherwise identical creatures apart while keeping the statblock
name ("Bandit" + nick "elf"). To give copies different nicks, write one entry per copy
instead of `count`. A nick can also be changed later:
`PATCH /encounters/<id>/combatants/<cid>` with `{"nick": "elf"}` (`""` or `null` removes it).

**Waves.** Use them when the user describes reinforcements, an ambush in stages, or
"then X arrives". Everything the party faces at the start is wave 0 (just omit `wave`).
Number later groups 1, 2, 3 in the order they arrive. Don't use waves to split up a
single group for no reason — an ordinary fight has only wave 0. Put the trigger for each
wave in `notes` ("wave 1 when the gate falls or at round 3"), since the app does not
start waves on its own.

The request is all-or-nothing:

| Status | Meaning | What to do |
|---|---|---|
| 201 | Encounter created, combat not started | Report the encounter name and `id` |
| 404 | A monster is not in the library (the message lists which) | Import or create it (step 2), then retry |
| 409 | A name matches several *different* statblocks (the message lists each id with its origin, CR and HP) | Pick the one that fits and retry that entry with `monster_id`; ask the user if unsure |
| 422 | Malformed body: both/neither of `monster` and `monster_id`, `count` outside 1–20, more than 50 entries, missing `name` | Fix the JSON |

## 4. After the fight is prepared

Nothing more is needed. The DM opens the encounter, adds the players and presses Start.
If asked to add a player through the API anyway:

```
POST /encounters/<id>/combatants        body: {"name": "Aria", "is_pc": true, "level": 5}
```

A monster can also be added to a wave afterwards:

```
POST /encounters/<id>/combatants        body: {"monster_id": 12, "count": 2, "wave": 1}
```

Without `wave` it joins the wave that is currently fighting.

Do not call `/encounters/<id>/start`, `next-turn`, `next-wave`, or change HP unless the
user asks — running the combat is the DM's job. `POST /encounters/<id>/next-wave` brings
the next waiting wave into a running fight (409 if the fight has not started or no wave
is waiting); in the app the DM is asked to confirm first, so only call it on an explicit
request.

## Typical flow

1. Read the user's request and list the creatures and how many of each.
2. `GET /monsters/?search=…` for each — note the ones already in the library.
3. For the missing ones: search Open5e and import by slug; write homebrew JSON only for
   custom creatures.
4. `POST /encounters/prepare` with the exact library names.
5. Tell the user what was added to the library, what the fight contains, and anything
   that failed.
