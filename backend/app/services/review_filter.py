"""Reglas de negocio de RepuSense para clasificación y filtrado de reseñas.

Define qué considera el negocio como una queja accionable (RF2: rating <= 3 y
texto no vacío), independientemente de la plataforma de origen (Google Maps,
Yelp, etc.). La regla pura vive en ``app.core.review_rules`` para compartirla
con infrastructure sin violar la arquitectura por capas.
"""

from typing import Any

from app.core.review_rules import seleccionar_negativas


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
    return seleccionar_negativas(resenas, cantidad, max_estrellas)
