"""Contrato de una reseña extraída de una plataforma de mapas."""

from pydantic import BaseModel, Field


class Resena(BaseModel):
    """Reseña individual, en la forma exacta que devuelve ``app.etl.resenas``.

    ``id`` es la clave de identidad para deduplicar en la persistencia, igual
    que ``place_id`` en ``app.schemas.discovery.Negocio``.

    ``fecha`` conserva el texto relativo que entrega la fuente (``"Hace 2
    meses"``) en lugar de un timestamp: el endpoint no expone la fecha real.
    """

    estrellas: int | None = Field(default=None, ge=1, le=5)
    fecha: str | None = None
    autor: str | None = None
    id: str = ""
    texto: str = ""
