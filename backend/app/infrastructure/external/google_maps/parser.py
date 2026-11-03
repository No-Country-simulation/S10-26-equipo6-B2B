"""Parsing, sanitización y normalización posicional de reseñas de Google Maps.

Funciones puras sin red y sin dependencias externas:
- Decodificación y limpieza de texto HTML.
- Parseo de timestamps a datetime UTC.
- Normalización posicional del payload de Google a diccionarios con nombres de campo.
- Cálculo del histograma de estrellas.
"""

import html
import re
from datetime import UTC, datetime
from typing import Any


def limpiar_texto(valor: Any) -> str:
    """Convierte los ``<br>`` en saltos de línea y decodifica entidades HTML."""
    if not isinstance(valor, str):
        return ""
    valor = re.sub(r"<br\s*/?>", "\n", valor, flags=re.I)
    return html.unescape(valor).strip()


def parsear_epoch_ms(valor: Any) -> datetime | None:
    """Convierte el epoch en milisegundos del payload a ``datetime`` UTC.

    La fuente lo serializa como string de 13 dígitos en la posición 2 de la
    lista de fecha, un nivel más adentro que el texto relativo. Devuelve
    ``None`` cuando falta o no se puede leer.
    """
    if not isinstance(valor, (str, int)) or isinstance(valor, bool):
        return None
    try:
        return datetime.fromtimestamp(int(valor) / 1000, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def extraer_campos(resena: list[Any]) -> dict[str, Any]:
    """Mapea los índices posicionales del JSON a campos con nombre."""
    fecha_lista = resena[2] if len(resena) > 2 and isinstance(resena[2], list) else None
    autor_lista = resena[3] if len(resena) > 3 and isinstance(resena[3], list) else None
    epoch_ms = fecha_lista[2] if fecha_lista and len(fecha_lista) > 2 else None

    # El texto aparece en varios índices; se prefiere 27, luego 28 y luego 11.
    texto = ""
    for indice in (27, 28, 11):
        if indice < len(resena) and isinstance(resena[indice], str) and resena[indice].strip():
            texto = limpiar_texto(resena[indice])
            break

    return {
        "estrellas": resena[1] if len(resena) > 1 else None,
        "fecha": (fecha_lista or [None])[0] if fecha_lista else None,
        "fecha_absoluta": parsear_epoch_ms(epoch_ms),
        "autor": (autor_lista or [None])[0] if autor_lista else None,
        "id": resena[5] if len(resena) > 5 else "",
        "texto": texto,
    }


def _parsear_resenas(resenas: list[list[Any]]) -> list[dict[str, Any]]:
    """Normaliza una lista cruda de reseñas con ``extraer_campos``."""
    return [extraer_campos(resena) for resena in resenas]


def resumen_distribucion(resenas: list[dict[str, Any]]) -> dict[int, int]:
    """Histograma de estrellas, que la API oficial de Places no expone."""
    conteo: dict[int, int] = {}
    for resena in resenas:
        estrellas = resena.get("estrellas")
        if estrellas is not None:
            conteo[estrellas] = conteo.get(estrellas, 0) + 1
    return dict(sorted(conteo.items(), reverse=True))
