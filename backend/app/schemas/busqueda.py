"""DTOs de creación y consulta de búsquedas de prospección."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchCreate(BaseModel):
    """Parámetros de entrada de una prospección."""

    sector: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    max_rating: float = Field(default=3.5, ge=0, le=5)
    min_reviews: int = Field(default=10, ge=0)


class SearchResponse(BaseModel):
    """Respuesta inmediata al crear una búsqueda."""

    model_config = ConfigDict(from_attributes=True)

    search_id: UUID
    sector: str
    city: str
    status: str
    created_at: datetime


class SearchStatusResponse(BaseModel):
    """Estado consolidado de una búsqueda y sus leads encontrados."""

    search_id: UUID
    status: str
    leads_encontrados: int = 0
    error_message: str | None = None
