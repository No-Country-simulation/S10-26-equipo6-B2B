"""DTOs de consulta y actualización de leads."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.ai import AIAnalysisResponse

LEAD_STATUSES = {"NEW", "CONTACTED", "DISCARDED"}


class LeadResponse(BaseModel):
    """Vista de un lead para el dashboard comercial."""

    model_config = ConfigDict(from_attributes=True)

    business_id: UUID
    name: str
    sector: str | None = None
    city: str | None = None
    rating: float | None = None
    total_reviews: int | None = None
    phone_number: str | None = None
    website: str | None = None
    lead_status: str
    created_at: datetime
    ai_analysis: AIAnalysisResponse | None = None


class LeadStatusUpdate(BaseModel):
    """Cambio de estado comercial de un lead."""

    lead_status: str

    @field_validator("lead_status")
    @classmethod
    def validar_estado(cls, value: str) -> str:
        estado = value.upper()
        if estado not in LEAD_STATUSES:
            permitidos = ", ".join(sorted(LEAD_STATUSES))
            raise ValueError(f"lead_status debe ser uno de: {permitidos}")
        return estado
