"""Inyección de dependencias de la API."""

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import SessionLocal, get_db
from app.infrastructure.external.google_maps_client import GoogleMapsClient
from app.infrastructure.external.serpapi_client import SerpApiDiscovery
from app.repositories.business_repo import BusinessRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.search_repo import SearchRepository
from app.services.prospecting_service import ProspectingService


def get_db_session() -> Generator[Session, None, None]:
    """Entrega una sesión de SQLAlchemy y la cierra al terminar la petición."""
    yield from get_db()


def get_prospecting_service(
    db: Annotated[Session, Depends(get_db_session)],
) -> ProspectingService:
    """Ensambla el servicio con sus repositorios y clientes de infraestructura."""
    return ProspectingService(
        search_repo=SearchRepository(),
        business_repo=BusinessRepository(),
        review_repo=ReviewRepository(),
        serp_client=SerpApiDiscovery(),
        maps_client=GoogleMapsClient(),
    )


def get_session_factory() -> Callable[[], Session]:
    """Entrega la fábrica de sesiones para tareas asíncronas en segundo plano."""
    return SessionLocal

