from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import RegisterTortoise

from app.api.v1.routes import monsters, encounters, open5e, characters
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RegisterTortoise(
        app,
        config=settings.TORTOISE_ORM,
        generate_schemas=False,
        add_exception_handlers=True,
    ):
        yield


app = FastAPI(title="InitiativeKeep API", lifespan=lifespan)

app.include_router(monsters.router, prefix="/api/v1/monsters", tags=["monsters"])
app.include_router(encounters.router, prefix="/api/v1/encounters", tags=["encounters"])
app.include_router(open5e.router, prefix="/api/v1/open5e", tags=["open5e"])
app.include_router(characters.router, prefix="/api/v1/characters", tags=["characters"])

_spa_dir = Path(__file__).parent.parent / "frontend_dist"
if _spa_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_spa_dir), html=True), name="spa")
