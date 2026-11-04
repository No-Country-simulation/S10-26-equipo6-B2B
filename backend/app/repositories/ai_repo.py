"""Repositorio de análisis con IA y catálogo de categorías de problemas."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import AIAnalysis, ProblemCategory
from app.schemas.ai import CATALOGO_CATEGORIAS


class AIRepository:
    """Persistencia idempotente de ``ai_analysis`` y maestro de ``problem_category``."""

    model = AIAnalysis

    def get_by_business_id(self, db: Session, business_id: UUID) -> AIAnalysis | None:
        """Devuelve el análisis vinculado a un negocio cargando su categoría."""
        stmt = (
            select(AIAnalysis)
            .options(joinedload(AIAnalysis.problem_category))
            .where(AIAnalysis.business_id == business_id)
        )
        return db.scalar(stmt)

    def ensure_categories(self, db: Session) -> dict[str, ProblemCategory]:
        """Asegura la existencia de las categorías del catálogo controlado."""
        existentes = list(db.scalars(select(ProblemCategory)))
        mapa: dict[str, ProblemCategory] = {c.name: c for c in existentes}

        nuevas = False
        for nombre in CATALOGO_CATEGORIAS:
            if nombre not in mapa:
                categoria = ProblemCategory(name=nombre)
                db.add(categoria)
                mapa[nombre] = categoria
                nuevas = True

        if nuevas:
            db.flush()

        return mapa

    def upsert_analysis(
        self,
        db: Session,
        business_id: UUID,
        problem_category_id: int,
        pain_points_summary: str,
        email_subject: str,
        email_first_paragraph: str,
        ai_model: str,
    ) -> AIAnalysis:
        """Inserta o actualiza el análisis de forma idempotente para un negocio."""
        now = datetime.now(UTC)
        existente = self.get_by_business_id(db, business_id)

        if existente is not None:
            existente.problem_category_id = problem_category_id
            existente.pain_points_summary = pain_points_summary
            existente.email_subject = email_subject
            existente.email_first_paragraph = email_first_paragraph
            existente.ai_model = ai_model
            existente.generated_at = now
            analisis = existente
        else:
            analisis = AIAnalysis(
                business_id=business_id,
                problem_category_id=problem_category_id,
                pain_points_summary=pain_points_summary,
                email_subject=email_subject,
                email_first_paragraph=email_first_paragraph,
                ai_model=ai_model,
                generated_at=now,
            )
            db.add(analisis)

        db.flush()
        return analisis
