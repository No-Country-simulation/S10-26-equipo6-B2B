"""Filtros y reglas de negocio para selección de reseñas de RepuSense."""

from typing import Any


def extraer_negativas(
    reseñas: list[dict[str, Any]], cantidad: int, max_estrellas: int = 3
) -> list[dict[str, Any]]:
    """Las N reseñas negativas más recientes que tengan texto.

    Una reseña es negativa cuando su ``rating <= max_estrellas`` y su
    ``content`` no está vacío (RF2 de ``docs/systemDesign.md``). Las reseñas
    sin cuerpo se descartan para que no consuman una de las plazas.
    """
    return [
        reseña
        for reseña in reseñas
        if reseña.get("estrellas") is not None
        and reseña["estrellas"] <= max_estrellas
        and reseña.get("texto")
    ][:cantidad]

