"""Servicio de análisis de reseñas con IA y personalización de cold emails (RF4)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import AIAnalysis, Business
from app.repositories.ai_repo import AIRepository
from app.schemas.ai import CATEGORIA_FALLBACK
from app.services.protocols import AIProviderProtocol

logger = logging.getLogger(__name__)


class AIService:
    """Orquesta la inferencia LLM y la persistencia de análisis y cold email por lead."""

    def __init__(
        self,
        ai_repo: AIRepository,
        ai_provider: AIProviderProtocol,
    ) -> None:
        self.ai_repo = ai_repo
        self.ai_provider = ai_provider

    def obtener_analisis(self, db: Session, business_id: UUID) -> AIAnalysis | None:
        """Recupera el análisis de IA existente para un negocio o ``None``."""
        return self.ai_repo.get_by_business_id(db, business_id)

    def analizar_negocio(self, db: Session, business_id: UUID) -> AIAnalysis | None:
        """Ejecuta el análisis sobre las reseñas del lead y persiste el resultado."""
        business = db.get(Business, business_id)
        if business is None:
            return None

        textos_resenas: list[str] = []
        for source in business.sources:
            for review in source.reviews:
                if review.content and (review.rating is None or review.rating <= 3):
                    textos_resenas.append(review.content)

        resultado = self.ai_provider.analizar_resenas(
            nombre_negocio=business.name,
            rubro=business.sector or "Negocio",
            resenas=textos_resenas,
        )

        categorias = self.ai_repo.ensure_categories(db)
        categoria_obj = categorias.get(resultado.category) or categorias.get(CATEGORIA_FALLBACK)
        if categoria_obj is None:
            # Fallback de seguridad si el catálogo estaba inicialmente vacío
            categoria_obj = next(iter(categorias.values()))

        analisis = self.ai_repo.upsert_analysis(
            db=db,
            business_id=business_id,
            problem_category_id=categoria_obj.problem_category_id,
            pain_points_summary=resultado.pain_points_summary,
            email_subject=resultado.email_subject,
            email_first_paragraph=resultado.email_first_paragraph,
            ai_model=resultado.ai_model,
        )
        db.commit()
        return analisis
