"""Proceso worker desacoplado para procesamiento de tareas de prospección desde Redis."""

import logging
import signal
import sys
import time
from collections.abc import Callable
from types import FrameType
from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.database.session import SessionLocal
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("repusense.worker")

_ejecutando = True


def _capturar_senales(signum: int, _frame: FrameType | None) -> None:
    global _ejecutando
    nombre_senal = signal.Signals(signum).name
    logger.info("Señal %s recibida. Deteniendo worker ordenadamente...", nombre_senal)
    _ejecutando = False


def instanciar_servicio(queue: RedisTaskQueue | None = None) -> ProspectingService:
    """Instancia el servicio de prospección con todas sus dependencias."""
    ai_service = AIService(
        ai_repo=AIRepository(),
        ai_provider=LLMClient(),
    )
    enrichment_service = ContactEnrichmentService(
        contact_repo=ContactRepository(),
        enricher=WebsiteScraper(),
    )
    return ProspectingService(
        search_repo=SearchRepository(),
        business_repo=BusinessRepository(),
        review_repo=ReviewRepository(),
        serp_client=SerpApiDiscovery(),
        maps_client=GoogleMapsClient(filtro_fn=extraer_negativas),
        task_queue=queue or RedisTaskQueue(),
        ai_service=ai_service,
        enrichment_service=enrichment_service,
    )


def procesar_siguiente_tarea(
    queue: RedisTaskQueue,
    service: ProspectingService,
    session_factory: Callable[[], Session],
    timeout: int = 2,
) -> UUID | None:
    """Extrae y procesa una sola tarea de la cola. Retorna el search_id procesado."""
    search_id = queue.desencolar(timeout=timeout)
    if search_id is None:
        return None

    logger.info("Worker inició procesamiento de búsqueda: %s", search_id)
    inicio = time.perf_counter()
    try:
        with session_factory() as db:
            service.ejecutar_prospeccion_sync(db, search_id)
        duracion = time.perf_counter() - inicio
        logger.info("Worker completó búsqueda %s en %.2fs", search_id, duracion)
    except Exception as error:
        logger.exception("Error al procesar búsqueda %s en worker: %s", search_id, error)
    return search_id


def iniciar_worker(
    queue: RedisTaskQueue | None = None,
    service: ProspectingService | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> None:
    """Loop principal de consumo de la cola Redis."""
    global _ejecutando

    signal.signal(signal.SIGINT, _capturar_senales)
    signal.signal(signal.SIGTERM, _capturar_senales)

    cola = queue or RedisTaskQueue()
    servicio = service or instanciar_servicio(cola)
    db_factory = session_factory or SessionLocal

    logger.info(
        "Worker de RepuSense iniciado. Conectado a Redis (%s), escuchando cola '%s'",
        cola.url,
        cola.queue_key,
    )

    while _ejecutando:
        try:
            procesar_siguiente_tarea(cola, servicio, db_factory, timeout=2)
        except Exception as error:
            logger.error("Fallo inesperado en loop del worker: %s", error)
            time.sleep(1.0)

    logger.info("Worker finalizado con éxito.")


if __name__ == "__main__":
    try:
        iniciar_worker()
    except Exception as err:
        logger.critical("Error fatal en el worker: %s", err)
        sys.exit(1)
