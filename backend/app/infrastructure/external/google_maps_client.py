"""Cliente de reseñas de Google Maps: fachada y adaptador de infraestructura.

Implementa ``ReviewProviderProtocol`` delegando en submódulos SRP:
- ``google_maps.protocol``: transporte HTTP y formato RPC GetLocalBoqProxy.
- ``google_maps.parser``: decodificación HTML y mapeo posicional del payload.
- ``app.core.review_rules``: regla de filtrado de reseñas negativas (RF2).
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.core.review_rules import seleccionar_negativas
from app.infrastructure.external.google_maps import parser, protocol
from app.infrastructure.external.google_maps.parser import (
    _parsear_resenas,
    extraer_campos,
    limpiar_texto,
    parsear_epoch_ms,
    resumen_distribucion,
)
from app.infrastructure.external.google_maps.protocol import (
    HEADERS,
    ORDENES,
    PAUSA_ENTRE_CANDIDATOS,
    PAUSA_ENTRE_PAGINAS,
    URL_BUSQUEDA,
    URL_RESENAS,
    USER_AGENT,
    ErrorRecoleccion,
    GoogleMapsError,
    construir_payload,
    extraer_cid,
    http_get,
    parsear_cid,
)
from app.schemas.resenas import Resena


def obtener_cids(consulta: str) -> list[str]:
    """Paso 1: busca el lugar y devuelve sus CID candidatos."""
    return protocol.obtener_cids(consulta)


def obtener_pagina(
    cid: str, orden: int, tamano_pagina: int, token: str | None = None
) -> tuple[list[Any], str | None]:
    """Paso 2: pide una página de reseñas y devuelve (reseñas, token_siguiente)."""
    return protocol.obtener_pagina(cid, orden, tamano_pagina, token)


def obtener_resenas(
    consulta: str,
    orden: int = 2,
    tamano_pagina: int = 20,
    max_paginas: int = 6,
    max_resenas: int = 100,
    *,
    obtener_cids_fn: Callable[..., Any] | None = None,
    obtener_pagina_fn: Callable[..., Any] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Recorre las páginas de un lugar, deduplicando por review ID."""
    buscar_cids = obtener_cids_fn or obtener_cids
    pedir_pagina = obtener_pagina_fn or obtener_pagina

    cids = buscar_cids(consulta)
    if not cids:
        raise ErrorRecoleccion("la búsqueda no devolvió ningún CID válido")

    for cid in cids[:4]:
        vistas: set[str] = set()
        salida: list[dict[str, Any]] = []
        token: str | None = None
        pagina = 0
        while pagina < max_paginas and len(salida) < max_resenas:
            resenas, token = pedir_pagina(cid, orden, tamano_pagina, token)
            nuevas = 0
            for resena in resenas:
                campos = extraer_campos(resena)
                review_id = campos.get("id")
                if review_id and review_id in vistas:
                    continue
                if review_id:
                    vistas.add(review_id)
                salida.append(campos)
                nuevas += 1
            pagina += 1
            if not token or nuevas == 0:
                break
            time.sleep(PAUSA_ENTRE_PAGINAS)

        if salida:
            momento = datetime.now(UTC)
            for campos in salida:
                campos["scraped_at"] = momento
            return salida, cid
        time.sleep(PAUSA_ENTRE_CANDIDATOS)

    raise ErrorRecoleccion(
        f"ninguno de los {min(len(cids), 4)} CID candidatos devolvió reseñas"
    )


def obtener_negativas(consulta: str, cantidad: int = 5) -> list[dict[str, Any]]:
    """Las ``cantidad`` reseñas negativas más recientes de un negocio."""
    from app.core.config import settings

    resenas, _cid = obtener_resenas(consulta)
    return seleccionar_negativas(resenas, cantidad, settings.etl_negative_rating_max)


class GoogleMapsClient:
    """Adaptador de la fuente de reseñas que implementa ReviewProviderProtocol.

    Satisface SRP y DIP aceptando opcionalmente una función de filtrado
    inyectada (por ejemplo, ``app.services.review_filter.extraer_negativas``).
    """

    def __init__(
        self,
        *,
        orden: int = 2,
        tamano_pagina: int = 20,
        max_paginas: int = 6,
        max_resenas: int = 100,
        filtro_fn: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        self._orden = orden
        self._tamano_pagina = tamano_pagina
        self._max_paginas = max_paginas
        self._max_resenas = max_resenas
        self._filtro_fn = filtro_fn

    def obtener_resenas(
        self,
        consulta: str,
        cantidad: int = 5,
    ) -> list[Resena]:
        """Devuelve las reseñas negativas más recientes ya validadas."""
        from app.core.config import settings

        resenas, _cid = obtener_resenas(
            consulta,
            orden=self._orden,
            tamano_pagina=self._tamano_pagina,
            max_paginas=self._max_paginas,
            max_resenas=self._max_resenas,
        )
        if self._filtro_fn is not None:
            candidatas = self._filtro_fn(
                resenas,
                cantidad,
                max_estrellas=settings.etl_negative_rating_max,
            )
        else:
            candidatas = seleccionar_negativas(
                resenas,
                cantidad,
                settings.etl_negative_rating_max,
            )
        return [Resena(**campos) for campos in candidatas]


__all__ = [
    "HEADERS",
    "ORDENES",
    "PAUSA_ENTRE_CANDIDATOS",
    "PAUSA_ENTRE_PAGINAS",
    "URL_BUSQUEDA",
    "URL_RESENAS",
    "USER_AGENT",
    "ErrorRecoleccion",
    "GoogleMapsClient",
    "GoogleMapsError",
    "_parsear_resenas",
    "construir_payload",
    "extraer_campos",
    "extraer_cid",
    "http_get",
    "limpiar_texto",
    "obtener_cids",
    "obtener_negativas",
    "obtener_pagina",
    "obtener_resenas",
    "parsear_cid",
    "parsear_epoch_ms",
    "parser",
    "protocol",
    "resumen_distribucion",
]
