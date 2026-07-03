# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

InitiativeKeep — combat/initiative tracker for D&D 2024 (5.5e). FastAPI backend (REST API), frontend TBD.
Sibling project **BoardGamesCounter** is the reference for conventions, Docker, and deployment.

## Running

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
- **Combatant** — a participant. Optional FK to a Monster (spawns from statblock) or a plain PC.
  Tracks `initiative`, `current_hp`/`max_hp`/`temp_hp`, `conditions` (JSON list).

Initiative order: highest `initiative` first, `dex_modifier` as tiebreak, unrolled (null) last.
Sorting is computed in `services/encounter.py` (not a DB order_by) — see `_initiative_key`.

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
- [ ] pytest suite in `backend/tests/`
- [x] Open5e browse/filter + bulk import (3200+ monsters — scraping deemed unnecessary)
- [ ] Frontend (React + Vite, like BoardGamesCounter)
- [ ] Auth (deferred — add later, as BGC did)
- [ ] Docker + Render/Neon deploy
```
