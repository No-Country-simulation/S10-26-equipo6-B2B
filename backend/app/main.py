"""Punto de entrada de la API de RepuSense."""

from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint de salud para healthchecks y smoke tests."""
    return {"status": "ok", "version": settings.version}
