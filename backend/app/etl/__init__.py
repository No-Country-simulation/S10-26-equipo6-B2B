"""Capa ETL: extracción y transformación de fuentes externas."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.etl.resenas import (
        ErrorRecoleccion,
        extraer_negativas,
        obtener_negativas,
        obtener_resenas,
    )

__all__ = [
    "ErrorRecoleccion",
    "extraer_negativas",
    "obtener_negativas",
    "obtener_resenas",
]


def __getattr__(nombre):
    """Resuelve los símbolos reexportados solo cuando se piden.

    El import va por aquí, no en caliente: cargar ``resenas`` al importar el
    paquete duplica el módulo cuando se ejecuta ``python -m app.etl.resenas``
    y runpy emite un RuntimeWarning.
    """
    if nombre in __all__:
        from app.etl import resenas

        return getattr(resenas, nombre)
    raise AttributeError(f"el módulo {__name__!r} no tiene el atributo {nombre!r}")
