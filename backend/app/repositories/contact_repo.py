"""Repositorio de persistencia de datos de contacto (RF3)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Contact


class ContactRepository:
    """Persistencia idempotente de contactos asociados a un lead."""

    model = Contact

    def list_by_business(self, db: Session, business_id: UUID) -> list[Contact]:
        """Devuelve todos los contactos registrados para un negocio."""
        stmt = (
            select(Contact)
            .where(Contact.business_id == business_id)
            .order_by(Contact.created_at.asc())
        )
        return list(db.scalars(stmt))

    def save_contacts(
        self,
        db: Session,
        business_id: UUID,
        emails: list[str],
        source: str = "BUSINESS_WEBSITE",
    ) -> list[Contact]:
        """Inserta correos electrónicos evitando duplicados para el mismo negocio."""
        if not emails:
            return []

        existentes = {
            c.value.lower()
            for c in self.list_by_business(db, business_id)
            if c.contact_type == "EMAIL"
        }

        guardados: list[Contact] = []
        for email in emails:
            email_limpio = email.strip().lower()
            if email_limpio in existentes:
                continue

            nuevo = Contact(
                business_id=business_id,
                contact_type="EMAIL",
                value=email_limpio,
                source=source,
            )
            db.add(nuevo)
            existentes.add(email_limpio)
            guardados.append(nuevo)

        if guardados:
            db.flush()

        return guardados
