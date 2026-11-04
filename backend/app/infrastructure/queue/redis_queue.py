"""Cola de tareas de prospección sobre Redis para procesamiento desacoplado."""

import logging
from uuid import UUID

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_KEY = "repusense:tasks:prospecting"


class RedisTaskQueue:
    """Implementación de cola FIFO sobre Redis usando listas (LPUSH/BRPOP)."""

    def __init__(
        self,
        url: str | None = None,
        queue_key: str = DEFAULT_QUEUE_KEY,
    ) -> None:
        self.url = url or settings.redis_url
        self.queue_key = queue_key
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=5.0,
            )
        return self._client

    def encolar(self, search_id: UUID) -> bool:
        """Encola un search_id al inicio de la lista de tareas."""
        try:
            self.client.lpush(self.queue_key, str(search_id))
            logger.info("Búsqueda %s encolada en Redis (%s)", search_id, self.queue_key)
            return True
        except Exception as error:
            logger.warning("Fallo al encolar %s en Redis: %s", search_id, error)
            return False

    def desencolar(self, timeout: int = 5) -> UUID | None:
        """Extrae el siguiente search_id del final de la lista (bloqueante hasta timeout)."""
        try:
            resultado = self.client.brpop(self.queue_key, timeout=timeout)
            if not resultado:
                return None
            _clave, valor = resultado
            return UUID(valor)
        except Exception as error:
            logger.warning("Fallo al desencolar de Redis: %s", error)
            return None

    def esta_disponible(self) -> bool:
        """Verifica conectividad contra el servidor Redis."""
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def tamano_cola(self) -> int:
        """Cantidad de tareas pendientes en la cola."""
        try:
            return int(self.client.llen(self.queue_key))
        except Exception:
            return 0
