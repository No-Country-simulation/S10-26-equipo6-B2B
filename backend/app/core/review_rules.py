"""Regla pura de negocio RF2 para clasificar resenas negativas.

Reside en la capa core (base) para que tanto ``app.services.review_filter``
como ``app.infrastructure`` puedan delegar en una unica implementacion sin
violar la arquitectura por capas: nadie importa hacia arriba.
"""

from typing import Any


def seleccionar_negativas(
    resenas: list[dict[str, Any]],
    cantidad: int,
    max_estrellas: int,
) -> list[dict[str, Any]]:
    """Selecciona las N resenas negativas mas recientes que contengan texto.

    Una resena es negativa cuando su ``estrellas <= max_estrellas`` y su campo
    ``texto`` no esta vacio (RF2 de ``docs/systemDesign.md``). Las resenas sin
    cuerpo se descartan para no consumir plazas utiles para el analisis de IA.
    """
    return [
        resena
        for resena in resenas
        if resena.get("estrellas") is not None
        and resena["estrellas"] <= max_estrellas
        and resena.get("texto")
    ][:cantidad]
