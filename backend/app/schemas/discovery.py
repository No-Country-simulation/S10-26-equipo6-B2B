"""Salida normalizada del discovery: un negocio candidato a lead."""

from pydantic import BaseModel


class Negocio(BaseModel):
    """Negocio obtenido por rubro y ciudad, ya filtrado por el brief.

    place_id es la clave de identidad para deduplicar en la persistencia.
    """

    nombre: str
    rating: float
    total_resenas: int
    place_id: str
    telefono: str | None = None
    website: str | None = None
    direccion: str | None = None
    rubro: str | None = None
    estado_operativo: str | None = None
