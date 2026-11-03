"""Filtros de negocio para detección de reseñas negativas en RepuSense."""

from typing import Any


def extraer_negativas(
    resenas: list[dict[str, Any]], cantidad: int, max_estrellas: int = 3
) -> list[dict[str, Any]]:
    """Las N reseñas negativas más recientes que tengan texto.

    Una reseña es negativa cuando su ``rating <= max_estrellas`` y su
    ``content`` no está vacío (RF2 de ``docs/systemDesign.md``). Las reseñas
    sin cuerpo se descartan para que no consuman una de las plazas.
    """
    return [
        resena
        for resena in resenas
        if resena.get("estrellas") is not None
        and resena["estrellas"] <= max_estrellas
        and resena.get("texto")
    ][:cantidad]
