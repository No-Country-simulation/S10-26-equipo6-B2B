"""Servicio de enriquecimiento secundario de datos de contacto (RF3)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import Contact
from app.repositories.business_repo import BusinessRepository
from app.repositories.contact_repo import ContactRepository
from app.services.protocols import ContactEnricherProtocol

logger = logging.getLogger(__name__)


class ContactEnrichmentService:
    """Orquesta el rastreo web y la persistencia de correos electrónicos por lead."""

    def __init__(
        self,
        contact_repo: ContactRepository,
        enricher: ContactEnricherProtocol,
        business_repo: BusinessRepository | None = None,
    ) -> None:
        self.contact_repo = contact_repo
        self.enricher = enricher
        self.business_repo = business_repo or BusinessRepository()

    def listar_contactos(self, db: Session, business_id: UUID) -> list[Contact]:
        """Devuelve los contactos registrados para el lead."""
        return self.contact_repo.list_by_business(db, business_id)

    def enriquecer_contactos(
        self,
        db: Session,
        business_id: UUID,
        commit: bool = True,
    ) -> list[Contact]:
        """Extrae correos desde el sitio web del negocio y los guarda sin duplicar."""
        business = self.business_repo.get_by_id(db, business_id)
        if business is None:
            return []

        if not business.website:
            return self.listar_contactos(db, business_id)

        try:
            emails = self.enricher.extraer_emails(business.website)
            if emails:
                self.contact_repo.save_contacts(db, business_id, emails)
                if commit:
                    db.commit()
        except Exception as error:
            logger.warning(
                "Fallo no bloqueante al enriquecer contactos de %r (%s): %s",
                business.name,
                business.website,
                error,
            )

        return self.listar_contactos(db, business_id)
