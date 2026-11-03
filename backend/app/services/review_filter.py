"""Reglas de negocio de RepuSense para clasificación y filtrado de reseñas.

Reside en la capa de servicios porque define qué considera el negocio como una
queja accionable (RF2: rating <= 3 y texto no vacío), independientemente de la
plataforma de origen (Google Maps, Yelp, etc.).
"""

from typing import Any


def extraer_negativas(
    resenas: list[dict[str, Any]],
    cantidad: int,
    max_estrellas: int = 3,
) -> list[dict[str, Any]]:
    """Selecciona las N reseñas negativas más recientes que contengan texto.

    Una reseña es negativa cuando su ``estrellas <= max_estrellas`` y su campo
    ``texto`` no está vacío (RF2 de ``docs/systemDesign.md``). Las reseñas sin
    cuerpo se descartan para no consumir plazas útiles para el análisis de IA.
    """
    return [
        resena
        for resena in resenas
        if resena.get("estrellas") is not None
        and resena["estrellas"] <= max_estrellas
        and resena.get("texto")
    ][:cantidad]
