# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

InitiativeKeep — combat/initiative tracker for D&D 2024 (5.5e). FastAPI backend (REST API), frontend TBD.
Sibling project **BoardGamesCounter** is the reference for conventions, Docker, and deployment.

## Quick start (Docker — runs everything)

From the repo root:
```powershell
docker compose up --build
```
Then open **http://localhost:8000** — one container builds the React frontend and
serves it from the FastAPI backend; data is stored in a SQLite file on the `ikdata`
volume (survives restarts). Stop with `docker compose down`. This is also the image
we deploy to AWS later (swap `DATABASE_URL` for a real Postgres).

Relevant files: `Dockerfile` (multi-stage: node builds SPA → python runs API),
`docker-compose.yml`, `entrypoint.sh` (runs `aerich upgrade` then uvicorn).

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
- **Character** — a saved PC (name, `max_hp`, `level`) in a reusable party roster
  (`services/character.py`, `/api/v1/characters`). Pick one to drop into an encounter
  as a PC combatant without re-typing; PCs carry a `level` that drives difficulty.
- **Combatant** — a participant. Optional FK to a Monster (spawns from statblock) or a plain PC.
  Tracks `initiative`, `level` (PC), `current_hp`/`max_hp`/`temp_hp`, `concentrating`,
  `conditions` (JSON list of `{"name", "rounds": int|null}`; timed ones tick down at end of
  round in `next_turn`, legacy plain strings are normalized on read), and a legendary action
  pool (`legendary_actions_max/_remaining`, set to 3 when spawned from a monster that has
  `legendary_actions`; refills at the start of the creature's turn).
  `CombatantCreate.count` (1–20) spawns N auto-numbered copies.

Initiative order: highest `initiative` first, `dex_modifier` as tiebreak, unrolled (null) last.
Sorting is computed in `services/encounter.py` (not a DB order_by) — see `_initiative_key`.

**Start combat** (`start_combat`) rolls initiative = d20 + dex_modifier for **every**
combatant (PCs included — the frontend "Prowadź walkę" run mode relies on this), and
rerolls monster HP from the linked statblock's `hit_dice` (e.g. `2d6`). PCs keep their
entered HP. Dice logic in `services/dice.py` (`roll_expr`, `roll_initiative`);
`roll_expr` parses `NdM+K`, clamps to min 1, falls back to a default.

**Open5e browse** re-ranks text-query results by name relevance (exact → prefix →
word-boundary → contains → matched-elsewhere) since the API's `search` is full-text and
name-sorted, which otherwise buries the obvious hit — see `_name_rank` in `services/open5e.py`.

## API (key endpoints)

- `GET/POST/PATCH/DELETE /api/v1/monsters` — homebrew CRUD, `?search=`
- `GET  /api/v1/open5e/monsters` — browse Open5e (3200+ statblocks), filters:
  `?q=`, `?cr=`, `?type=`, `?document=` (source slug), `?page=`; paginated (20/page)
- `GET  /api/v1/open5e/sources` — list document sources (srd, tob, cc, ...) for filters
- `POST /api/v1/open5e/import/{slug}` — import one statblock (idempotent by slug)
- `POST /api/v1/open5e/import` — bulk import `{"slugs": [...]}` → `{imported, failed}`
- `GET/POST/PATCH/DELETE /api/v1/encounters`
- `POST/PATCH/DELETE /api/v1/encounters/{id}/combatants[/{cid}]`
- `POST /api/v1/encounters/{id}/start | next-turn | prev-turn` — combat control

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
│   ├── EncounterList.tsx      list/create/delete encounters
│   ├── EncounterTracker.tsx   combat view: round + turn controls (start/next/prev),
│   │                          combatant rows (initiative, HP bar + dmg/heal, conditions),
│   │                          roll-unrolled-initiative, add combatant (from monster or PC)
│   ├── MonsterBrowser.tsx     Open5e browse/filter/import + homebrew "My Library"
│   └── MonsterDetail.tsx      statblock modal (abilities, AC/HP/CR, speed, traits, actions)
├── App.css                   all styles (no UI library), dark theme
└── index.css                 reset + body
```

No auth (backend has none yet). No router — `App.tsx` switches views via state.

## Database

- ORM: Tortoise ORM (async). Migrations: aerich.
- Dev: SQLite (`sqlite://./db.sqlite3`). Prod: PostgreSQL via `DATABASE_URL` (Neon).

Init migrations (first time), from `backend/`:
```powershell
..\.venv\Scripts\python.exe -m aerich init-db
```
Run migrations: `..\.venv\Scripts\python.exe -m aerich upgrade`

## Deployment Plan (mirror BoardGamesCounter)

Target: **Render** (web service, free tier) + **Neon.tech** (PostgreSQL, free tier).
TODO: Dockerfile, docker-compose, entrypoint (`aerich upgrade` + uvicorn), GitHub Actions CI/CD.

## Status / TODO

- [x] Backend scaffold, models, monster CRUD, Open5e import, encounter + combat control
- [x] aerich migrations + E2E smoke test (import → encounter → combatants → turns)
- [x] pytest suite in `backend/tests/` (dice, open5e, monsters, characters, encounters)
- [x] Open5e browse/filter + bulk import (3200+ monsters — scraping deemed unnecessary)
- [x] Frontend (React + Vite + TS): encounter tracker, HP/conditions, Open5e browse/import
- [ ] Auth (deferred — add later, as BGC did)
- [ ] Docker + Render/Neon deploy
```
