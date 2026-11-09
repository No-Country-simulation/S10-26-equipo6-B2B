"""Inyección de dependencias de la API."""

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import SessionLocal, get_db
from app.infrastructure.external.google_maps_client import GoogleMapsClient
from app.infrastructure.external.llm_client import LLMClient
from app.infrastructure.external.serpapi_client import SerpApiDiscovery
from app.infrastructure.external.website_scraper import WebsiteScraper
from app.infrastructure.queue.redis_queue import RedisTaskQueue
from app.repositories.ai_repo import AIRepository
from app.repositories.business_repo import BusinessRepository
from app.repositories.contact_repo import ContactRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.search_repo import SearchRepository
from app.services.ai_service import AIService
from app.services.enrichment_service import ContactEnrichmentService
from app.services.prospecting_service import ProspectingService
from app.services.review_filter import extraer_negativas


def get_db_session() -> Generator[Session, None, None]:
    """Entrega una sesión de SQLAlchemy y la cierra al terminar la petición."""
    yield from get_db()


def get_task_queue() -> RedisTaskQueue:
    """Entrega el cliente de cola de tareas sobre Redis."""
    return RedisTaskQueue()


def get_ai_service() -> AIService:
    """Entrega el servicio de análisis de reseñas y cold email con IA."""
    return AIService(
        ai_repo=AIRepository(),
        ai_provider=LLMClient(),
    )


def get_contact_enrichment_service() -> ContactEnrichmentService:
    """Entrega el servicio de enriquecimiento secundario de contactos web."""
    return ContactEnrichmentService(
        contact_repo=ContactRepository(),
        enricher=WebsiteScraper(),
    )


def get_maps_client() -> GoogleMapsClient:
    """Entrega el cliente de Google Maps inyectando la regla de filtrado de negocio (DIP)."""
    return GoogleMapsClient(filtro_fn=extraer_negativas)


def get_prospecting_service(
    db: Annotated[Session, Depends(get_db_session)],
    task_queue: Annotated[RedisTaskQueue, Depends(get_task_queue)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    enrichment_service: Annotated[
        ContactEnrichmentService, Depends(get_contact_enrichment_service)
    ],
    maps_client: Annotated[GoogleMapsClient, Depends(get_maps_client)],
) -> ProspectingService:
    """Ensambla el servicio con sus repositorios y clientes de infraestructura."""
    return ProspectingService(
        search_repo=SearchRepository(),
        business_repo=BusinessRepository(),
        review_repo=ReviewRepository(),
        serp_client=SerpApiDiscovery(),
        maps_client=maps_client,
        task_queue=task_queue,
        ai_service=ai_service,
        enrichment_service=enrichment_service,
    )


def get_session_factory() -> Callable[[], Session]:
    """Entrega la fábrica de sesiones para tareas asíncronas en segundo plano."""
    return SessionLocal

