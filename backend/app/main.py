"""Punto de entrada de la API de RepuSense."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.infrastructure.database.session import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Inicializa el esquema del MVP sin impedir el arranque si la BD no está."""
    try:
        init_db()
    except Exception as error:  # el healthcheck debe seguir disponible
        logger.warning("No se pudo inicializar la base de datos al arrancar: %s", error)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint de salud para healthchecks y smoke tests."""
    return {"status": "ok", "version": settings.version}
