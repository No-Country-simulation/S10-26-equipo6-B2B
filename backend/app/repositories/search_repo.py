"""Repositorio de búsquedas y de su relación con los negocios."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Search, SearchBusiness

SEARCH_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"}
TERMINAL_STATUSES = {"COMPLETED", "FAILED"}


class SearchRepository:
    """Operaciones de persistencia sobre ``search`` y ``search_business``."""

    model = Search

    def get(self, db: Session, entity_id: UUID) -> Search | None:
        return self.get_by_id(db, entity_id)

    def create_search(
        self,
        db: Session,
        sector: str,
        city: str,
        max_rating: float,
        min_reviews: int,
    ) -> Search:
        """Registra una búsqueda nueva en estado ``PENDING``."""
        search = Search(
            sector=sector,
            city=city,
            max_rating=Decimal(str(max_rating)),
            min_reviews=min_reviews,
            status="PENDING",
        )
        db.add(search)
        db.flush()
        return search

    def get_by_id(self, db: Session, search_id: UUID) -> Search | None:
        return db.get(Search, search_id)

    def update_status(
        self,
        db: Session,
        search_id: UUID,
        status: str,
        error_message: str | None = None,
    ) -> Search:
        """Actualiza el estado y las marcas temporales de la ejecución."""
        estado = status.upper()
        if estado not in SEARCH_STATUSES:
            raise ValueError(f"estado de búsqueda no válido: {status}")

        search = self.get_by_id(db, search_id)
        if search is None:
            raise ValueError(f"búsqueda no encontrada: {search_id}")

        ahora = datetime.now(UTC)
        search.status = estado
        search.error_message = error_message

        if estado == "IN_PROGRESS" and search.started_at is None:
            search.started_at = ahora
        if estado in TERMINAL_STATUSES:
            search.finished_at = ahora

        db.flush()
        return search

    def link_business(
        self,
        db: Session,
        search_id: UUID,
        business_id: UUID,
    ) -> None:
        """Vincula un negocio con la búsqueda, sin duplicar la relación."""
        existente = db.get(SearchBusiness, (search_id, business_id))
        if existente is not None:
            return
        db.add(SearchBusiness(search_id=search_id, business_id=business_id))
        db.flush()

    def count_leads(self, db: Session, search_id: UUID) -> int:
        """Cuenta los negocios vinculados a una búsqueda."""
        total = db.scalar(
            select(func.count(func.distinct(SearchBusiness.business_id))).where(
                SearchBusiness.search_id == search_id
            )
        )
        return int(total or 0)
