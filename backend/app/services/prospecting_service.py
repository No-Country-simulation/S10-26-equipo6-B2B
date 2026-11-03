"""Casos de uso de prospección: discovery, reseñas y persistencia."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import Business, Search
from app.repositories.business_repo import BusinessRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.search_repo import SearchRepository
from app.schemas.busqueda import SearchCreate
from app.services.protocols import DiscoveryProviderProtocol, ReviewProviderProtocol

logger = logging.getLogger(__name__)


class ProspectingService:
    """Orquesta el caso de uso completo de una prospección."""

    def __init__(
        self,
        search_repo: SearchRepository,
        business_repo: BusinessRepository,
        review_repo: ReviewRepository,
        serp_client: DiscoveryProviderProtocol,
        maps_client: ReviewProviderProtocol,
    ) -> None:
        self.search_repo = search_repo
        self.business_repo = business_repo
        self.review_repo = review_repo
        self.serp_client = serp_client
        self.maps_client = maps_client

    def iniciar_busqueda(self, db: Session, datos: SearchCreate) -> Search:
        """Registra la búsqueda en estado ``PENDING`` para respuesta inmediata."""
        search = self.search_repo.create_search(
            db,
            sector=datos.sector,
            city=datos.city,
            max_rating=datos.max_rating,
            min_reviews=datos.min_reviews,
        )
        db.commit()
        return search

    def obtener_busqueda(self, db: Session, search_id: UUID) -> Search | None:
        return self.search_repo.get_by_id(db, search_id)

    def contar_leads(self, db: Session, search_id: UUID) -> int:
        return self.search_repo.count_leads(db, search_id)

    def ejecutar_prospeccion_sync(self, db: Session, search_id: UUID) -> None:
        """Ejecuta discovery y reseñas de forma síncrona (MVP sin workers).

        Cada negocio se persiste de forma idempotente, se vincula a la búsqueda
        y, si la fuente de reseñas responde, se guardan sus reseñas negativas.
        Un fallo aislado de reseñas no tumba la prospección completa.
        """
        search = self.search_repo.get_by_id(db, search_id)
        if search is None:
            raise ValueError(f"búsqueda no encontrada: {search_id}")

        self.search_repo.update_status(db, search_id, "IN_PROGRESS")
        db.commit()

        try:
            platform = self.business_repo.ensure_platform(db)
            negocios = self.serp_client.buscar_negocios(search.sector, search.city)

            for negocio in negocios:
                source = self.business_repo.upsert_from_discovery(
                    db,
                    negocio,
                    platform.platform_id,
                )
                self.business_repo.enrich_search_context(
                    db,
                    source.business_id,
                    sector=search.sector,
                    city=search.city,
                )
                self.search_repo.link_business(db, search_id, source.business_id)
                db.flush()

                resenas = self._obtener_resenas(negocio.nombre, search.city)
                if resenas:
                    self.review_repo.save_many(
                        db,
                        source.business_source_id,
                        resenas,
                    )
                db.commit()

            self.search_repo.update_status(db, search_id, "COMPLETED")
            db.commit()
        except Exception as error:  # se persiste el fallo y se informa
            logger.exception("Falló la prospección %s", search_id)
            db.rollback()
            try:
                self.search_repo.update_status(
                    db,
                    search_id,
                    "FAILED",
                    str(error),
                )
                db.commit()
            except Exception:  # último recurso: no ocultar el fallo original
                logger.exception("No se pudo registrar el fallo de la búsqueda %s", search_id)
                db.rollback()

    def listar_leads(
        self,
        db: Session,
        search_id: UUID | None = None,
        city: str | None = None,
        sector: str | None = None,
        lead_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Business], int]:
        """Devuelve la página de leads y el total que cumple los filtros."""
        return self.business_repo.list_leads(
            db,
            search_id=search_id,
            city=city,
            sector=sector,
            lead_status=lead_status,
            page=page,
            page_size=page_size,
        )

    def actualizar_lead_status(
        self,
        db: Session,
        business_id: UUID,
        lead_status: str,
    ) -> Business | None:
        """Actualiza el estado comercial y confirma la transacción."""
        business = self.business_repo.update_lead_status(db, business_id, lead_status)
        if business is None:
            return None
        db.commit()
        return business

    def _obtener_resenas(self, nombre: str, city: str):
        consulta = f"{nombre} {city}".strip()
        try:
            return self.maps_client.obtener_resenas(consulta)
        except Exception as error:  # la reseña es enriquecimiento opcional
            logger.warning("No se pudieron extraer reseñas de %r: %s", consulta, error)
            return []
