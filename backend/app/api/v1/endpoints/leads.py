"""Endpoints de leads para el dashboard comercial."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_prospecting_service
from app.models.entities import Business, BusinessSource
from app.schemas.common import PaginatedResponse
from app.schemas.lead import LeadResponse, LeadStatusUpdate
from app.services.prospecting_service import ProspectingService

router = APIRouter(prefix="/leads", tags=["Leads"])


def _mejor_fuente(sources: list[BusinessSource]) -> BusinessSource | None:
    if not sources:
        return None
    return max(
        sources,
        key=lambda source: source.last_scraped_at.isoformat() if source.last_scraped_at else "",
    )


def _a_lead_response(business: Business) -> LeadResponse:
    source = _mejor_fuente(business.sources)
    return LeadResponse(
        business_id=business.business_id,
        name=business.name,
        sector=business.sector,
        city=business.city,
        rating=float(source.rating) if source and source.rating is not None else None,
        total_reviews=source.total_reviews if source else None,
        phone_number=business.phone_number,
        website=business.website,
        lead_status=business.lead_status,
        created_at=business.created_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Lista leads filtrados y paginados",
)
def listar_leads(
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ProspectingService, Depends(get_prospecting_service)],
    search_id: Annotated[UUID | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    sector: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[LeadResponse]:
    """Devuelve la página de leads con el formato ``PaginatedResponse``."""
    businesses, total = service.listar_leads(
        db,
        search_id=search_id,
        city=city,
        sector=sector,
        lead_status=status,
        page=page,
        page_size=limit,
    )
    return PaginatedResponse[LeadResponse](
        items=[_a_lead_response(business) for business in businesses],
        total=total,
        page=page,
        page_size=limit,
    )


@router.patch(
    "/{lead_id}/status",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualiza el estado comercial de un lead",
)
def actualizar_estado_lead(
    lead_id: UUID,
    datos: LeadStatusUpdate,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ProspectingService, Depends(get_prospecting_service)],
) -> LeadResponse:
    """Cambia ``lead_status`` y registra ``contacted_at`` cuando aplica."""
    business = service.actualizar_lead_status(db, lead_id, datos.lead_status)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"lead no encontrado: {lead_id}",
        )
    return _a_lead_response(business)
