"""Endpoints de búsquedas de prospección."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_prospecting_service, get_session_factory
from app.schemas.busqueda import SearchCreate, SearchResponse, SearchStatusResponse
from app.services.prospecting_service import ProspectingService

router = APIRouter(prefix="/busquedas", tags=["Búsquedas"])


def _ejecutar_prospeccion_background(
    service: ProspectingService,
    search_id: UUID,
    session_factory: Callable[[], Session],
) -> None:
    """Ejecuta la prospección en segundo plano con una sesión de BD aislada."""
    with session_factory() as db:
        service.ejecutar_prospeccion_sync(db, search_id)


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inicia una prospección",
)
def crear_busqueda(
    datos: SearchCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ProspectingService, Depends(get_prospecting_service)],
    session_factory: Annotated[Callable[[], Session], Depends(get_session_factory)],
) -> SearchResponse:
    """Crea la búsqueda y delega la prospección pesada a segundo plano.

    Responde inmediatamente con el snapshot ``PENDING`` (202 Accepted).
    El cliente monitorea el progreso asíncrono con ``GET /api/v1/busquedas/{id}``.
    """
    search = service.iniciar_busqueda(db, datos)
    respuesta = SearchResponse.model_validate(search)
    background_tasks.add_task(
        _ejecutar_prospeccion_background,
        service,
        search.search_id,
        session_factory,
    )
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
