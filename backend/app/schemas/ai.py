"""Esquemas Pydantic para el análisis de reseñas con IA y generación de cold email."""

import logging
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

CATALOGO_CATEGORIAS: list[str] = [
    "Atención al cliente",
    "Tiempos de espera",
    "Precios y facturación",
    "Calidad del servicio",
    "Higiene e instalaciones",
    "Otros",
]

CATEGORIA_FALLBACK = "Otros"


class AIAnalysisResult(BaseModel):
    """Resultado estructurado devuelto por el proveedor de inferencia de IA."""

    model_config = ConfigDict(from_attributes=True)

    category: str = Field(
        ...,
        description="Categoría principal del problema según el catálogo controlado.",
    )
    pain_points_summary: str = Field(
        ...,
        description="Resumen de puntos de dolor extraídos de las reseñas negativas.",
    )
    email_subject: str = Field(
        ...,
        description="Asunto persuasivo y personalizado para el cold email.",
    )
    email_first_paragraph: str = Field(
        ...,
        description="Gancho inicial personalizado que aborda el problema detectado.",
    )
    ai_model: str = Field(
        default="mock-heuristic-v1",
        description="Identificador del modelo de IA que generó el análisis.",
    )

    @field_validator("category", mode="before")
    @classmethod
    def validar_y_sanitizar_categoria(cls, value: str) -> str:
        """Escudo anti-alucinación: si la categoría no está en el catálogo, mapea a 'Otros'."""
        if not isinstance(value, str):
            logger.warning(
                "[LLM_HALLUCINATION_DETECTED] Categoría no es string (%r). Mapeando a %s",
                value,
                CATEGORIA_FALLBACK,
            )
            return CATEGORIA_FALLBACK

        categoria_limpia = value.strip()
        for cat in CATALOGO_CATEGORIAS:
            if cat.lower() == categoria_limpia.lower():
                return cat

        logger.warning(
            "[LLM_HALLUCINATION_DETECTED] Categoría no permitida recibida: %r. Mapeando a %s.",
            categoria_limpia,
            CATEGORIA_FALLBACK,
        )
        return CATEGORIA_FALLBACK


class AIAnalysisResponse(BaseModel):
    """DTO para exponer el análisis de IA persistido en la API."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    business_id: UUID
    category: str
    pain_points_summary: str | None = None
    email_subject: str | None = None
    email_first_paragraph: str | None = None
    ai_model: str | None = None
    generated_at: datetime
