# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

InitiativeKeep — combat/initiative tracker for D&D 2024 (5.5e). FastAPI backend (REST API)
+ React/Vite/TS frontend, deployed on Render (Docker) with Neon Postgres.
Sibling project **BoardGamesCounter** is the reference for conventions, Docker, and deployment.

## Quick start (Docker — runs everything)

From the repo root:
```powershell
docker compose up --build
```
Then open **http://localhost:8000** — one container builds the React frontend and
serves it from the FastAPI backend; data is stored in a SQLite file on the `ikdata`
volume (survives restarts). Stop with `docker compose down`. This is the same image
deployed to Render (there `DATABASE_URL` points at a Neon Postgres instead).

Relevant files: `Dockerfile` (multi-stage: node builds SPA → python runs API),
`docker-compose.yml`, `entrypoint.sh` (runs `init_db.py` then uvicorn),
`render.yaml` (Render blueprint).

## Running (without Docker, for development)

Backend dev server (from `backend/`):
```powershell
..\.venv\Scripts\uvicorn.exe app.main:app --reload
```
Auto docs (Swagger) at http://localhost:8000/docs

## Environment

- Python virtual environment at `.venv/` (Python 3.14) — repo root, shared by backend.
- Install deps: `.venv\Scripts\pip.exe install -r backend\requirements-dev.txt`
- Backend deps: `backend/requirements.txt` (prod), `backend/requirements-dev.txt` (+ pytest)

## Architecture

```
InitiativeKeep/
├── backend/                  FastAPI REST API
│   ├── app/
│   │   ├── main.py           App entry, lifespan (Tortoise), router registration
│   │   ├── config.py         Settings via pydantic-settings (.env), DATABASE_URL, TORTOISE_ORM
│   │   ├── models/           Tortoise ORM models
│   │   │   ├── monster.py    Monster statblock (open5e or homebrew)
│   │   │   └── encounter.py  Encounter + Combatant (turn/round state)
│   │   ├── schemas/          Pydantic request/response schemas
│   │   │   ├── monster.py
│   │   │   └── encounter.py
│   │   ├── services/         Business logic (DB queries, combat rules, Open5e client)
│   │   │   ├── monster.py
│   │   │   ├── encounter.py  initiative sort, start/next/prev turn, round advance
│   │   │   └── open5e.py     httpx client: search + import from api.open5e.com
│   │   └── api/v1/routes/    Thin HTTP handlers → delegate to services
│   │       ├── monsters.py
│   │       ├── encounters.py
│   │       └── open5e.py
│   ├── migrations/           aerich DB migrations
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml        aerich + pytest config
│   └── .env.example
└── .venv/                    Python 3.14 virtual environment
```

Layering: **route → service → model**. Routes stay thin; combat rules and external
calls live in services.

## Domain

- **Monster** — a statblock. `source` = "open5e" (imported, `is_homebrew=False`) or "homebrew".
  `dex_modifier` = `(dexterity - 10) // 2` (property).
- **Encounter** — one combat. `round` (starts 1), `current_turn_index` (index into the
  initiative-sorted combatant list; `-1` = combat not started).
- **Waves** — reinforcements. `Combatant.wave` (default 0) and `Encounter.current_wave`
  (default 0): combatants with `wave <= current_wave` are fighting, the rest wait in
  reserve. An encounter that never uses a wave above 0 behaves exactly as before.
  `_sorted_combatants` returns the fighters in initiative order followed by the reserve
  (by wave, then id) — `current_turn_index` only ever points into the first part, and
  `next_turn`/`prev_turn` wrap on `_active_count`. `start_combat` resets `current_wave`
  to 0 and rolls only wave 0; `start_next_wave` (`POST /{id}/next-wave`) moves to the
  lowest waiting wave number (gaps allowed), rolls its initiative/HP via `_roll_in`, and
  re-points `current_turn_index` at whoever was acting, since newcomers may sort above
  them. It is snapshotted ("start wave N"), so Undo sends the wave back. A new combatant
  with no `wave` joins `current_wave`. The frontend lists the reserve under "Wave N ·
  waiting" headings and asks `confirm()` before starting a wave.
- **EncounterSnapshot** — undo history. Every combat mutation (add/update/remove
  combatant, start/end, next/prev turn, next wave) first saves the whole encounter state
  (round, turn index, all combatant rows) with a human label via `_snapshot` in
  `services/encounter.py`; `undo` restores the latest one (re-creating removed
  combatants under their old id) and deletes it. Capped at `UNDO_LIMIT` (50) per
  encounter. `EncounterOut.undo_label` = what Undo would revert (null = nothing).
  No-op PATCHes add no history.
- **Character** — a saved PC (name, `max_hp`, `level`) in a reusable party roster
  (`services/character.py`, `/api/v1/characters`). Pick one to drop into an encounter
  as a PC combatant without re-typing; PCs carry a `level` that drives difficulty.
- **Combatant** — a participant. Optional FK to a Monster (spawns from statblock) or a plain PC.
  `nick` (nullable, ≤100) = the DM's tag beside the name ("elf", "Skarr") — separate from
  `name`, so auto-numbering and the statblock name stay intact; blank/null clears it. Set via
  `CombatantCreate`/`CombatantUpdate`/prepare's `enemies[].nick`; edited in place in the
  tracker (`NickTag`, monsters only).
  Tracks `initiative`, `level` (PC), `current_hp`/`max_hp`/`temp_hp`, `concentrating`,
  `conditions` (JSON list of `{"name", "rounds": int|null}`; timed ones tick down at end of
  round in `next_turn`, legacy plain strings are normalized on read), and a legendary action
  pool (`legendary_actions_max/_remaining`, set to 3 when spawned from a monster that has
  `legendary_actions`; refills at the start of the creature's turn).
  `recharge_used` (JSON `[{"name", "round"}]`) = spent recharge abilities; cleared by
  `start_combat`. The app never rolls the d6 — the DM rolls physical dice. The frontend
  parses "(Recharge 5–6)" / "(Recharge 6)" / "(Recharges after a … Rest)" from the linked
  statblock's ability names (`rechargeAbilities` in `EncounterTracker.tsx`) and, on the
  creature's turn from the round after use, asks "Roll d6 … Recharged / No".
  Concentration checks are frontend-only: each hit on a concentrating monster queues a
  CON save DC = min(30, max(10, dmg/2)) with Kept / Lost; 0 HP drops concentration.
  `CombatantCreate.count` (1–20) spawns N auto-numbered copies.

Initiative order: highest `initiative` first, `dex_modifier` as tiebreak, unrolled (null) last.
Sorting is computed in `services/encounter.py` (not a DB order_by) — see `_initiative_key`.

**Start combat** (`start_combat`) rolls initiative = d20 + dex_modifier for **every**
combatant (PCs included — the frontend rolls initiative for the whole party), and
rerolls monster HP from the linked statblock's `hit_dice` (e.g. `2d6`). PCs keep their
HP (the DM does not track player HP — the frontend hides PC HP entirely).
Dice logic in `services/dice.py` (`roll_expr`, `roll_initiative`);
`roll_expr` parses `NdM+K`, clamps to min 1, falls back to a default.

**Open5e browse** re-ranks text-query results by name relevance (exact → prefix →
word-boundary → contains → matched-elsewhere) since the API's `search` is full-text and
name-sorted, which otherwise buries the obvious hit — see `_name_rank` in `services/open5e.py`.

## API (key endpoints)

- `GET/POST/PATCH/DELETE /api/v1/monsters` — homebrew CRUD, `?search=`
- `POST /api/v1/monsters/import-json` — add a homebrew monster from a raw JSON
  statblock (native or Open5e shape; `special_abilities` → traits). Validated via
  `MonsterCreate`; bad JSON → 422. See `normalize_monster_payload` in `services/monster.py`.
  No duplicates: if the library already holds a statblock with the same name (any case)
  and the same stats (`find_identical` / `statblock_of`), nothing is added and that one
  is returned with 200 instead of 201. Same name + different stats is still added.
- `POST /api/v1/monsters/import-json/bulk` — many homebrew monsters at once: a JSON list,
  or `{"results"|"monsters": [...]}` (e.g. a saved Open5e page). Max 500. Per-item
  validation, partial success → 200 `{imported: [MonsterOut], skipped: [MonsterOut],
  failed: [{index, name, error}]}` (`skipped` = already in the library, incl. repeats
  inside the same paste);
  bad envelope / empty / over limit → 422. See `create_monsters_from_json`.
- `GET  /api/v1/open5e/monsters` — browse Open5e (3200+ statblocks), filters:
  `?q=`, `?cr=`, `?type=`, `?document=` (source slug), `?page=`; paginated (20/page)
- `GET  /api/v1/open5e/sources` — list document sources (srd, tob, cc, ...) for filters
- `POST /api/v1/open5e/import/{slug}` — import one statblock (idempotent by slug)
- `POST /api/v1/open5e/import` — bulk import `{"slugs": [...]}` → `{imported, failed}`
- `GET/POST/PATCH/DELETE /api/v1/encounters`
- `POST /api/v1/encounters/prepare` — prep a fight in one call:
  `{name, notes?, enemies: [{monster | monster_id, count 1–20, name?, nick?, wave 0–50}]}` (max 50 entries)
  → 201 `EncounterOut`, combat not started, no undo history. `monster` = library name
  (case-insensitive exact match), exactly one of `monster` / `monster_id` (else 422).
  All-or-nothing: unknown monster → 404, nothing created. A name shared by identical copies
  (`_same_statblock`, via `statblock_of` in `services/monster.py`) uses the oldest;
  shared by different statblocks → 409 listing each id with origin, CR and HP. PCs join later via `POST /{id}/combatants`.
  See `prepare_encounter` in `services/encounter.py`.
- `POST/PATCH/DELETE /api/v1/encounters/{id}/combatants[/{cid}]`
- `POST /api/v1/encounters/{id}/start | next-turn | prev-turn` — combat control
- `POST /api/v1/encounters/{id}/next-wave` — bring the next waiting wave into the running
  fight; 409 if combat has not started or no wave is waiting
- `POST /api/v1/encounters/{id}/undo` — revert the last change; 409 if nothing to undo

## Frontend (React + Vite + TypeScript)

Running (from `frontend/`):
```powershell
npm install
npm run dev      # http://localhost:5173  (proxies /api -> backend :8000)
npm run build    # tsc -b + vite build -> frontend/dist/
```
Backend must run on port 8000 for the dev proxy (`vite.config.ts`).

```
frontend/src/
├── main.tsx                  mounts <App />
├── App.tsx                   tab shell: Encounters | Monsters; holds active encounter
├── api/client.ts             typed fetch wrapper + all API calls (mirrors backend schemas)
├── components/
│   ├── EncounterList.tsx      list/create/delete encounters (cards: round seal,
│   │                          player/monster tags, started vs. not-started);
│   │                          Paste JSON dialog → `POST /encounters/prepare`
│   ├── EncounterSchema.tsx    prepared-encounter field table, library name/id table,
│   │                          example JSON (mirror of EncounterPrepare — update by hand)
│   ├── EncounterTracker.tsx   combat view: round + turn controls (start/next/prev/end,
│   │                          Undo button + Ctrl+Z outside text fields),
│   │                          combatant rows (initiative, AC shield / PC level medal,
│   │                          click-to-edit nick beside monster names,
│   │                          waves: reserve listed under "Wave N" headings, "Start wave N"
│   │                          button (confirm) during combat, wave field in the add form,
│   │                          monster HP bar + dmg/heal, conditions; PC HP not tracked),
│   │                          add combatant (from monster or PC),
│   │                          clicking a monster name docks its statblock in a side panel
│   ├── MonsterBrowser.tsx     Open5e browse/filter/import + homebrew "My Library";
│   │                          Paste JSON dialog (always `/import-json/bulk`; one object
│   │                          is wrapped in a list so "already there" is reported)
│   ├── MonsterEditor.tsx      homebrew statblock form; "?" shows field schema + live JSON
│   ├── StatblockSchema.tsx    shared statblock field table + JSON examples (mirror of
│   │                          MonsterCreate — update by hand when the schema changes)
│   └── MonsterDetail.tsx      statblock view (abilities, AC/HP/CR, speed, traits, actions);
│                              always rendered with `variant="panel"` (docked side panel);
│                              `variant="modal"` still supported but unused
├── App.css                   all styles (no UI library), parchment/fantasy theme
├── index.css                 reset + body + CSS custom properties (palette, type scale),
│                             light values on :root, dark overrides on [data-theme="dark"]
└── useTheme.ts               light/dark toggle (☀/☾ in the top bar), saved in localStorage
```

While the statblock panel is open the tracker sets `body.panel-open`, which shrinks
the page so rows are not hidden under the docked panel.

**Theming / dark mode:** App.css must not hard-code themed colours — use the tokens in
`index.css` (`--danger-*`, `--heal-*`, `--temp-*`, `--gold-wash-*`, `--heading`, …, and
`rgba(var(--shade|--crimson-rgb|--gold-rgb), a)` for tints/shadows). A new colour needs a
light value on `:root` **and** a dark value under `:root[data-theme="dark"]`. Exceptions
on purpose: the "metal" pieces (AC shield, PC medal, encounter seals, initiative arrow,
ability-hex rims) and HP bar fills look the same in both themes. The inline script in
`index.html` sets `data-theme` before first paint (saved choice, else OS setting) so
dark mode never flashes light; `useTheme.ts` keeps it in sync afterwards.

Fonts: **Cinzel** (headings) + **EB Garamond** (body), loaded from Google Fonts in
`frontend/index.html` — no network, no fonts: the CSS stack falls back to system serif.

No auth (backend has none yet). No router — `App.tsx` switches views via state.

## Database

- ORM: Tortoise ORM (async).
- Dev: SQLite (`sqlite://./db.sqlite3`). Prod: PostgreSQL via `DATABASE_URL` (Neon).

Schema is bootstrapped from the models at container start by `backend/init_db.py`
(`Tortoise.generate_schemas(safe=True)` → `CREATE TABLE IF NOT EXISTS`), **not** aerich.
The committed aerich migrations under `backend/migrations/` are SQLite-only SQL
(they use `AUTOINCREMENT`, which Postgres rejects) and are not the deploy path.
`generate_schemas` creates missing tables but does **not** ALTER existing ones. So
**a new column on an existing model must also be listed in `ADDED_COLUMNS` in
`backend/app/schema_upgrade.py`** (SQLite + Postgres DDL); `init_db.py` adds it with
`ALTER TABLE … ADD COLUMN` when missing, so it reaches Neon on the next deploy.
New tables need nothing extra.

## Deployment (Render + Neon)

Live on **Render** (Docker web service, free tier) with a **Neon.tech** Postgres
(free tier). Config is in-repo: `render.yaml` blueprint (`runtime: docker`,
`healthCheckPath: /docs`), `Dockerfile`, `entrypoint.sh` (`init_db.py` → uvicorn).
`DATABASE_URL` is set in the Render UI (`sync: false`), not committed.

**CI** — `.github/workflows/ci.yml` runs on push/PR to `main`: two jobs, backend
(`pytest` on Python 3.14) and frontend (`npm ci` + `npm run build` on Node 22).
Frontend build requires `frontend/package-lock.json` (tracked, for `npm ci`).

## Status / TODO

- [x] Backend scaffold, models, monster CRUD, Open5e import, encounter + combat control
- [x] aerich migrations + E2E smoke test (import → encounter → combatants → turns)
- [x] pytest suite in `backend/tests/` (dice, open5e, monsters, characters, encounters)
- [x] Open5e browse/filter + bulk import (3200+ monsters — scraping deemed unnecessary)
- [x] Frontend (React + Vite + TS): encounter tracker, HP/conditions, Open5e browse/import
- [x] CI: GitHub Actions (pytest + frontend build) on push/PR
- [x] Docker + Render/Neon deploy (live; `render.yaml` blueprint, schema from `init_db.py`)
- [x] Paste-JSON import for homebrew monsters (`POST /monsters/import-json`, `/import-json/bulk`)
- Auth intentionally out of scope — personal single-user app
```
