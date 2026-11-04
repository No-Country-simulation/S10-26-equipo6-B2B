"""Contratos abstractos (Protocols) para inversión de dependencias (DIP).

La capa de servicios depende de estas interfaces y nunca de las implementaciones
concretas de infraestructura (SerpApi, Google Maps, etc.).
"""

from typing import Protocol, runtime_checkable
from uuid import UUID

from app.schemas.discovery import Negocio
from app.schemas.resenas import Resena


@runtime_checkable
class DiscoveryProviderProtocol(Protocol):
    """Contrato para cualquier proveedor de descubrimiento de negocios."""

    def buscar_negocios(self, rubro: str, ciudad: str) -> list[Negocio]:
        """Devuelve negocios candidatos filtrados por rubro y ciudad."""
        ...


@runtime_checkable
class ReviewProviderProtocol(Protocol):
    """Contrato para cualquier extractor de reseñas de negocios."""

    def obtener_resenas(self, consulta: str, cantidad: int = 5) -> list[Resena]:
        """Devuelve las reseñas negativas más recientes validadas."""
        ...


@runtime_checkable
class TaskQueueProtocol(Protocol):
    """Contrato para encolamiento asíncrono de tareas de prospección."""

    def encolar(self, search_id: UUID) -> bool:
        """Encola el identificador de una búsqueda para procesamiento en segundo plano."""
        ...

    def desencolar(self, timeout: int = 5) -> UUID | None:
        """Extrae el siguiente search_id de la cola (bloqueante hasta timeout)."""
        ...
