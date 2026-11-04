"""Subpaquete de infraestructura para Google Maps aplicando SRP.

- ``protocol``: Transporte HTTP anónimo y construcción de payload RPC GetLocalBoqProxy.
- ``parser``: Limpieza de entidades HTML, conversión de epoch ms y mapeo posicional.
"""

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
    obtener_cids,
    obtener_pagina,
    parsear_cid,
)

__all__ = [
    "HEADERS",
    "ORDENES",
    "PAUSA_ENTRE_CANDIDATOS",
    "PAUSA_ENTRE_PAGINAS",
    "URL_BUSQUEDA",
    "URL_RESENAS",
    "USER_AGENT",
    "ErrorRecoleccion",
    "GoogleMapsError",
    "_parsear_resenas",
    "construir_payload",
    "extraer_campos",
    "extraer_cid",
    "http_get",
    "limpiar_texto",
    "obtener_cids",
    "obtener_pagina",
    "parsear_cid",
    "parsear_epoch_ms",
    "resumen_distribucion",
]
