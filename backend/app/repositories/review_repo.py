"""Repositorio de reseñas vinculadas a una ficha de plataforma."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.entities import Review
from app.schemas.resenas import Resena


class ReviewRepository:
    """Persistencia idempotente de ``review`` por ``(business_source_id, external_id)``."""

    model = Review

    def get(self, db: Session, entity_id: UUID) -> Review | None:
        return db.get(Review, entity_id)

    def save_many(
        self,
        db: Session,
        business_source_id: UUID,
        resenas: list[Resena],
    ) -> list[Review]:
        """Inserta o actualiza las reseñas recibidas y devuelve sus entidades."""
        if not resenas:
            return []

        guardadas: list[Review] = []
        now = datetime.now(UTC)
        for resena in resenas:
            valores = self._values(business_source_id, resena, now)

            if db.get_bind().dialect.name == "postgresql":
                statement = (
                    pg_insert(Review)
                    .values(**valores)
                    .on_conflict_do_update(
                        constraint="uq_review_source_external",
                        set_={
                            "author": valores["author"],
                            "rating": valores["rating"],
                            "content": valores["content"],
                            "reviewed_at": valores["reviewed_at"],
                            "scraped_at": valores["scraped_at"],
                        },
                    )
                    .returning(Review)
                )
                guardadas.append(db.execute(statement).scalar_one())
                continue

            existente = db.scalar(
                select(Review).where(
                    Review.business_source_id == business_source_id,
                    Review.external_id == valores["external_id"],
                )
            )
            if existente is None:
                existente = Review(**valores)
                db.add(existente)
            else:
                existente.author = valores["author"]
                existente.rating = valores["rating"]
                existente.content = valores["content"]
                existente.reviewed_at = valores["reviewed_at"]
                existente.scraped_at = valores["scraped_at"]
            guardadas.append(existente)

        db.flush()
        return guardadas

    def list_by_source(
        self,
        db: Session,
        business_source_id: UUID,
    ) -> list[Review]:
        return list(
            db.scalars(
                select(Review)
                .where(Review.business_source_id == business_source_id)
                .order_by(Review.reviewed_at.desc().nullslast())
            )
        )

    def _values(
        self,
        business_source_id: UUID,
        resena: Resena,
        now: datetime,
    ) -> dict:
        return {
            "business_source_id": business_source_id,
            "external_id": self._external_id(resena),
            "author": resena.autor,
            "rating": resena.estrellas,
            "content": resena.texto or None,
            "reviewed_at": resena.fecha_absoluta,
            "scraped_at": resena.scraped_at or now,
        }

    def _external_id(self, resena: Resena) -> str:
        if resena.id:
            return resena.id
        base = "|".join(
            [
                resena.autor or "",
                str(resena.estrellas),
                resena.fecha_absoluta.isoformat() if resena.fecha_absoluta else "",
                resena.texto,
            ]
        )
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return f"hash:{digest[:40]}"
