<div align="center">

# ⚔️ InitiativeKeep

**Combat & initiative tracker for D&D 2024 (5.5e)**

Run encounters, track HP and conditions, and pull from 3200+ monster statblocks — all in one place.

<sub>FastAPI · Tortoise ORM · React · Vite · TypeScript · SQLite/PostgreSQL · Docker</sub>

</div>

---

## ✨ Features

- **🎲 Combat tracker** — initiative order, round counter, next/prev turn, per-combatant HP bars, damage/heal, and temp HP (damage burns temp HP first).
- **🧠 Concentration** — flag a concentrating creature; when it takes damage the tracker shows the CON save DC (`max(10, dmg/2)`).
- **⏳ Timed conditions** — give any condition a duration in rounds; it counts down at the end of each round and expires on its own (or leave it open-ended).
- **👑 Legendary actions** — bosses get a clickable 3-orb pool that refills at the start of their turn; statblocks show reactions and legendary actions.
- **⚖️ Difficulty calculator** — set party size and level, get the encounter's XP total rated against the D&D 2024 Low/Moderate/High budgets live as you add monsters.
- **🐺 Pack spawning** — add N copies of a monster at once; duplicates are auto-numbered (`Wolf (1)`, `Wolf (2)`, …).
- **🧑‍🤝‍🧑 Party roster** — save your PCs (name, HP, level) once and drop them into any encounter with one click; no AC to enter for players.
- **🖥️ Run mode** — prep the fight, then launch a full-screen combat screen; initiative is rolled for every combatant (PCs included). Arrow keys / space advance turns.
- **⚖️ Smarter difficulty** — the budget is taken from your PCs' levels automatically, and monster XP is scaled by an encounter multiplier so packs read as harder than raw XP.
- **🐉 Monster library** — browse and filter [Open5e](https://open5e.com)'s 3200+ statblocks by CR, type, or source; import one at a time or in bulk.
- **🛠️ Statblock creator** — build your own NPCs and bosses with a full editor: size/type/AC/HP/hit dice, speeds, six ability scores, CR, and repeatable traits, actions, reactions, and legendary actions. Edit them anytime; a homebrew boss with legendary actions spawns with the 3-orb pool automatically.
- **📜 Auto rolls** — on combat start, NPCs roll initiative (`d20 + DEX`) and reroll HP from their hit dice; PCs keep the numbers you typed.
- **📖 Statblock detail** — full modal view: abilities, AC/HP/CR, speed, traits, and actions.
- **📱 Responsive** — works on phone and tablet: combatant cards reflow, tables scroll, and the condition picker is tap-friendly.
- **🐳 One-command run** — Docker builds the SPA and serves it from the API with a persistent SQLite volume.

## 🚀 Quick start (Docker)

From the repo root:

```powershell
docker compose up --build
```

Open **http://localhost:8000** — a single container builds the React frontend and serves it from the FastAPI backend. Data lives in a SQLite file on the `ikdata` volume (survives restarts). Stop with `docker compose down`.

This is also the image deployed to production (swap `DATABASE_URL` for real Postgres).

## 🧑‍💻 Local development

**Backend** (from `backend/`):

```powershell
..\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Swagger docs at **http://localhost:8000/docs**.

**Frontend** (from `frontend/`):

```powershell
npm install
npm run dev      # http://localhost:5173  — proxies /api -> backend :8000
npm run build    # tsc -b + vite build -> frontend/dist/
```

The backend must run on port 8000 for the dev proxy.

### Environment

- Python 3.14 virtualenv at `.venv/` (repo root, shared by backend).
- Install backend deps: `.venv\Scripts\pip.exe install -r backend\requirements-dev.txt`
- `backend/requirements.txt` (prod) · `backend/requirements-dev.txt` (+ pytest)

### Database

Tortoise ORM (async) with [aerich](https://github.com/tortoise/aerich) migrations. SQLite in dev, PostgreSQL in prod via `DATABASE_URL`.

```powershell
# first time, from backend/
..\.venv\Scripts\python.exe -m aerich init-db
# apply migrations
..\.venv\Scripts\python.exe -m aerich upgrade
```

## 🏛️ Architecture

Layering: **route → service → model**. Routes stay thin; combat rules and external calls live in services.

```
InitiativeKeep/
├── backend/                  FastAPI REST API
│   └── app/
│       ├── main.py           app entry, lifespan (Tortoise), routers
│       ├── config.py         pydantic-settings (.env), DATABASE_URL, TORTOISE_ORM
│       ├── models/           Tortoise ORM: monster, encounter, combatant
│       ├── schemas/          Pydantic request/response
│       ├── services/         combat rules, dice, Open5e httpx client
│       └── api/v1/routes/    thin HTTP handlers
├── frontend/                 React + Vite + TypeScript
│   └── src/
│       ├── App.tsx           tab shell: Encounters | Monsters
│       ├── api/client.ts     typed fetch wrapper (mirrors backend schemas)
│       └── components/       EncounterTracker, MonsterBrowser, MonsterDetail, ...
└── .venv/                    Python 3.14 virtualenv
```

### Domain

| Entity | What it is |
| --- | --- |
| **Monster** | A statblock. `source` = `open5e` (imported) or `homebrew`. `dex_modifier = (dexterity - 10) // 2`. |
| **Encounter** | One combat. `round` (starts 1), `current_turn_index` (`-1` = not started). |
| **Combatant** | A participant. Optional FK to a Monster, or a plain PC. Tracks initiative, HP/temp HP, conditions. |

Initiative order: highest `initiative` first, `dex_modifier` as tiebreak, unrolled (null) last — computed in `services/encounter.py`.

## 🔌 API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET/POST/PATCH/DELETE` | `/api/v1/monsters` | Homebrew CRUD (`?search=`) |
| `GET/POST/PATCH/DELETE` | `/api/v1/characters` | Saved PC roster (name, HP, level) |
| `GET` | `/api/v1/open5e/monsters` | Browse Open5e — `?q= &cr= &type= &document= &page=` (20/page) |
| `GET` | `/api/v1/open5e/sources` | List document sources for filters |
| `POST` | `/api/v1/open5e/import/{slug}` | Import one statblock (idempotent) |
| `POST` | `/api/v1/open5e/import` | Bulk import `{"slugs": [...]}` |
| `GET/POST/PATCH/DELETE` | `/api/v1/encounters` | Encounter CRUD |
| `POST/PATCH/DELETE` | `/api/v1/encounters/{id}/combatants[/{cid}]` | Manage combatants |
| `POST` | `/api/v1/encounters/{id}/start \| next-turn \| prev-turn` | Combat control |

## 🗺️ Roadmap

- [x] Backend: models, monster CRUD, Open5e import, encounter + combat control
- [x] aerich migrations + E2E smoke test
- [x] Open5e browse/filter + bulk import
- [x] Frontend: encounter tracker, HP/conditions, Open5e browse/import
- [x] Docker (multi-stage build, one-command run)
- [ ] pytest suite in `backend/tests/`
- [ ] Auth (deferred)
- [ ] Render + Neon deploy

---

<div align="center"><sub>Built for the D&D 2024 ruleset. No auth yet — run it locally or behind your own gate.</sub></div>
