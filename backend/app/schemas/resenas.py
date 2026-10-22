"""Contrato de una reseña extraída de una plataforma de mapas."""

from datetime import datetime

from pydantic import BaseModel, Field


class Resena(BaseModel):
    """Reseña individual, en la forma exacta que devuelve ``app.etl.resenas``.

    ``id`` es la clave de identidad para deduplicar en la persistencia, igual
    que ``place_id`` en ``app.schemas.discovery.Negocio``.

    ``fecha`` conserva el texto relativo de la fuente (``"Hace 2 meses"``) tal
    cual sirve para mostrar. ``fecha_absoluta`` trae el epoch en milisegundos
    que el mismo payload entrega un nivel más adentro: es la única con la que
    se puede ordenar y la que alimenta ``review.reviewed_at``. Queda en
    ``None`` cuando la fuente no lo trae o viene ilegible.

    ``scraped_at`` no viene del payload: lo estampa ``obtener_resenas`` con una
    hora por lote, que es lo que permite cronometrar la recolección y
    reprogramar reintentos (``review.scraped_at`` del ERD).
    """

    estrellas: int | None = Field(default=None, ge=1, le=5)
    fecha: str | None = None
    fecha_absoluta: datetime | None = None
    autor: str | None = None
    id: str = ""
    texto: str = ""
    scraped_at: datetime | None = None
