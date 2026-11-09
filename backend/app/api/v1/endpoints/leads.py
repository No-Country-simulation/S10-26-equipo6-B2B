"""Endpoints de leads para el dashboard comercial."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_ai_service,
    get_contact_enrichment_service,
    get_db_session,
    get_prospecting_service,
)
from app.models.entities import Business, BusinessSource
from app.schemas.ai import AIAnalysisResponse
from app.schemas.common import PaginatedResponse
from app.schemas.contact import ContactResponse
from app.schemas.lead import LeadResponse, LeadStatusUpdate
from app.services.ai_service import AIService
from app.services.enrichment_service import ContactEnrichmentService
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
    ai_dto = None
    if business.ai_analysis:
        cat_name = (
            business.ai_analysis.problem_category.name
            if business.ai_analysis.problem_category
            else "Otros"
        )
        ai_dto = AIAnalysisResponse(
            analysis_id=business.ai_analysis.analysis_id,
            business_id=business.business_id,
            category=cat_name,
            pain_points_summary=business.ai_analysis.pain_points_summary,
            email_subject=business.ai_analysis.email_subject,
            email_first_paragraph=business.ai_analysis.email_first_paragraph,
            ai_model=business.ai_analysis.ai_model,
            generated_at=business.ai_analysis.generated_at,
        )

    contact_dtos = [
        ContactResponse(
            contact_id=c.contact_id,
            business_id=c.business_id,
            contact_type=c.contact_type,
            value=c.value,
            source=c.source,
            created_at=c.created_at,
        )
        for c in (business.contacts or [])
    ]
    primer_email = next(
        (c.value for c in (business.contacts or []) if c.contact_type == "EMAIL"),
        None,
    )

    return LeadResponse(
        business_id=business.business_id,
        name=business.name,
        sector=business.sector,
        city=business.city,
        rating=float(source.rating) if source and source.rating is not None else None,
        total_reviews=source.total_reviews if source else None,
        phone_number=business.phone_number,
        website=business.website,
        email=primer_email,
        lead_status=business.lead_status,
        created_at=business.created_at,
        ai_analysis=ai_dto,
        contacts=contact_dtos,
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


@router.get(
    "/{lead_id}/ai-analysis",
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtiene el análisis de IA y cold email de un lead",
)
def obtener_analisis_ia(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> AIAnalysisResponse:
    """Devuelve el análisis generado con IA para este lead o 404 si aún no existe."""
    analisis = ai_service.obtener_analisis(db, lead_id)
    if analisis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análisis de IA no encontrado para el lead: {lead_id}",
        )
    return AIAnalysisResponse(
        analysis_id=analisis.analysis_id,
        business_id=analisis.business_id,
        category=analisis.problem_category.name if analisis.problem_category else "Otros",
        pain_points_summary=analisis.pain_points_summary,
        email_subject=analisis.email_subject,
        email_first_paragraph=analisis.email_first_paragraph,
        ai_model=analisis.ai_model,
        generated_at=analisis.generated_at,
    )


@router.post(
    "/{lead_id}/ai-analysis",
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Genera o regenera el análisis de IA y cold email para un lead",
)
def generar_analisis_ia(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> AIAnalysisResponse:
    """Ejecuta la inferencia de IA sobre las reseñas del lead y guarda el análisis."""
    analisis = ai_service.analizar_negocio(db, lead_id)
    if analisis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead no encontrado para análisis: {lead_id}",
        )
    return AIAnalysisResponse(
        analysis_id=analisis.analysis_id,
        business_id=analisis.business_id,
        category=analisis.problem_category.name if analisis.problem_category else "Otros",
        pain_points_summary=analisis.pain_points_summary,
        email_subject=analisis.email_subject,
        email_first_paragraph=analisis.email_first_paragraph,
        ai_model=analisis.ai_model,
        generated_at=analisis.generated_at,
    )


@router.get(
    "/{lead_id}/contacts",
    response_model=list[ContactResponse],
    status_code=status.HTTP_200_OK,
    summary="Lista los canales de contacto de un lead",
)
def listar_contactos_lead(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    enrichment_service: Annotated[
        ContactEnrichmentService, Depends(get_contact_enrichment_service)
    ],
) -> list[ContactResponse]:
    """Devuelve los correos electrónicos y medios de contacto encontrados para el lead."""
    contactos = enrichment_service.listar_contactos(db, lead_id)
    return [
        ContactResponse(
            contact_id=c.contact_id,
            business_id=c.business_id,
            contact_type=c.contact_type,
            value=c.value,
            source=c.source,
            created_at=c.created_at,
        )
        for c in contactos
    ]


@router.post(
    "/{lead_id}/enrich-contacts",
    response_model=list[ContactResponse],
    status_code=status.HTTP_200_OK,
    summary="Rastrea la web del negocio y extrae correos electrónicos",
)
def enriquecer_contactos_lead(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    enrichment_service: Annotated[
        ContactEnrichmentService, Depends(get_contact_enrichment_service)
    ],
) -> list[ContactResponse]:
    """Ejecuta el scraper sobre el sitio web del negocio y guarda los correos encontrados."""
    contactos = enrichment_service.enriquecer_contactos(db, lead_id)
    return [
        ContactResponse(
            contact_id=c.contact_id,
            business_id=c.business_id,
            contact_type=c.contact_type,
            value=c.value,
            source=c.source,
            created_at=c.created_at,
        )
        for c in contactos
    ]


