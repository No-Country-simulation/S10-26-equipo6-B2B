"""Contrato mínimo que cumplen los repositorios de persistencia."""

from typing import Any, Protocol, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class Repository(Protocol[ModelT]):
    """Protocolo genérico de acceso a datos.

    Los repositorios nunca importan capas de presentación ni de servicios:
    reciben una ``Session`` y devuelven entidades ORM.
    """

    model: type[ModelT]

    def get(self, db: Session, entity_id: Any) -> ModelT | None:
        """Devuelve una entidad por su clave primaria o ``None``."""
        ...
