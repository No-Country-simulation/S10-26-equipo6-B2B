"""Orquestación ETL de reseñas de Google Maps.

Fachada principal del módulo ETL de reseñas. Desacopla y coordina:
- Cliente y transporte HTTP (app.etl.cliente)
- Parser y normalización de datos (app.etl.parser)
- Reglas de filtrado del negocio (app.etl.filtros)
- Interfaz CLI y diagnóstico (app.etl.cli)

Implementación del contrato documentado en `docs/fuente-de-resenas.md`.
"""

import time
from datetime import UTC, datetime
from typing import Any

from app.etl import cliente
from app.etl.cli import correr_smoke_test, main
from app.etl.cliente import (
    HEADERS,
    ORDENES,
    PAUSA_ENTRE_CANDIDATOS,
    PAUSA_ENTRE_PAGINAS,
    URL_BUSQUEDA,
    URL_RESENAS,
    USER_AGENT,
    ErrorRecoleccion,
    construir_payload,
    http_get,
    parsear_cid,
)
from app.etl.filtros import extraer_negativas
from app.etl.parser import (
    extraer_campos,
    limpiar_texto,
    parsear_epoch_ms,
    resumen_distribucion,
)


def obtener_cids(consulta: str) -> list[str]:
    """Paso 1: busca el lugar y devuelve sus CID candidatos."""
    return cliente.obtener_cids(consulta)


def obtener_pagina(
    cid: str, orden: int, tamano_pagina: int, token: str | None = None
) -> tuple[list[Any], str | None]:
    """Paso 2: pide una página de reseñas y devuelve (reseñas, token_siguiente)."""
    return cliente.obtener_pagina(cid, orden, tamano_pagina, token)


def obtener_resenas(
    consulta: str,
    orden: int = 2,
    tamano_pagina: int = 20,
    max_paginas: int = 6,
    max_resenas: int = 100,
) -> tuple[list[dict[str, Any]], str]:
    """Recorre las páginas de un lugar, deduplicando por review ID.

    Devuelve (lista_de_reseñas, cid_utilizado).
    """
    cids = obtener_cids(consulta)
    if not cids:
        raise ErrorRecoleccion("la busqueda no devolvio ningun CID valido")

    for cid in cids[:4]:
        vistas: set[str] = set()
        salida: list[dict[str, Any]] = []
        token: str | None = None
        pagina = 0
        while pagina < max_paginas and len(salida) < max_resenas:
            reseñas, token = obtener_pagina(cid, orden, tamano_pagina, token)
            nuevas = 0
            for reseña in reseñas:
                campos = extraer_campos(reseña)
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
            # Una hora por lote: es la métrica que permite cronometrar la
            # recolección y reprogramar reintentos (ERD, systemDesign.md:281).
            momento = datetime.now(UTC)
            for campos in salida:
                campos["scraped_at"] = momento
            return salida, cid
        # CID valido pero sin reseñas: se prueba el siguiente candidato.
        time.sleep(PAUSA_ENTRE_CANDIDATOS)

    raise ErrorRecoleccion(
        f"ninguno de los {min(len(cids), 4)} CID candidatos devolvio resenas"
    )


def obtener_negativas(consulta: str, cantidad: int = 5) -> list[dict[str, Any]]:
    """Las ``cantidad`` reseñas negativas más recientes de un negocio.

    Función pública de la capa ETL: ejecuta la recolección completa y aplica
    el filtro de RF2 con el umbral de ``settings.etl_negative_rating_max``.
    Lanza ``ErrorRecoleccion`` cuando la fuente no responde.
    """
    from app.core.config import settings

    reseñas, _cid = obtener_resenas(consulta)
    return extraer_negativas(reseñas, cantidad, settings.etl_negative_rating_max)


__all__ = [
    "HEADERS",
    "ORDENES",
    "PAUSA_ENTRE_CANDIDATOS",
    "PAUSA_ENTRE_PAGINAS",
    "URL_BUSQUEDA",
    "URL_RESENAS",
    "USER_AGENT",
    "ErrorRecoleccion",
    "construir_payload",
    "correr_smoke_test",
    "extraer_campos",
    "extraer_negativas",
    "http_get",
    "limpiar_texto",
    "main",
    "obtener_cids",
    "obtener_negativas",
    "obtener_pagina",
    "obtener_resenas",
    "parsear_cid",
    "parsear_epoch_ms",
    "resumen_distribucion",
]


if __name__ == "__main__":
    main()
