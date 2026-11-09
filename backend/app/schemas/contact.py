"""DTOs de datos de contacto obtenidos durante el enriquecimiento secundario (RF3)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContactResponse(BaseModel):
    """Vista de un dato de contacto asociado a un lead comercial."""

    model_config = ConfigDict(from_attributes=True)

    contact_id: UUID
    business_id: UUID
    contact_type: str = Field(..., description="Tipo de contacto: EMAIL o LINKEDIN")
    value: str = Field(..., description="Correo electrónico o URL de contacto")
    source: str = Field(..., description="Origen: BUSINESS_WEBSITE o LINKEDIN_SEARCH")
    created_at: datetime
