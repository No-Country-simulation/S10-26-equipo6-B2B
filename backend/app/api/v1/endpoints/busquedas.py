"""Endpoints de búsquedas de prospección."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_prospecting_service
from app.schemas.busqueda import SearchCreate, SearchResponse, SearchStatusResponse
from app.services.prospecting_service import ProspectingService

router = APIRouter(prefix="/busquedas", tags=["Búsquedas"])


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inicia una prospección",
)
def crear_busqueda(
    datos: SearchCreate,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ProspectingService, Depends(get_prospecting_service)],
) -> SearchResponse:
    """Crea la búsqueda y ejecuta la prospección del MVP de forma síncrona.

    La respuesta es el snapshot ``PENDING`` que exige el contrato 202; el
    resultado final se consulta después con ``GET /busquedas/{id}``.
    """
    search = service.iniciar_busqueda(db, datos)
    respuesta = SearchResponse.model_validate(search)
    service.ejecutar_prospeccion_sync(db, search.search_id)
    return respuesta


@router.get(
    "/{search_id}",
    response_model=SearchStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta el estado de una búsqueda",
)
def consultar_busqueda(
    search_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ProspectingService, Depends(get_prospecting_service)],
) -> SearchStatusResponse:
    """Devuelve el estado y la cantidad de leads encontrados."""
    search = service.obtener_busqueda(db, search_id)
    if search is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"búsqueda no encontrada: {search_id}",
        )

    return SearchStatusResponse(
        search_id=search.search_id,
        status=search.status,
        leads_encontrados=service.contar_leads(db, search.search_id),
        error_message=search.error_message,
    )
