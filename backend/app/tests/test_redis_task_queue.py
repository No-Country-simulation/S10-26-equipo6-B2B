"""Pruebas unitarias de la cola de tareas Redis y el proceso worker."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.infrastructure.queue.redis_queue import RedisTaskQueue
from app.services.protocols import TaskQueueProtocol
from app.worker import procesar_siguiente_tarea


class FakeRedisClient:
    """Simulador en memoria de las primitivas LPUSH y BRPOP de Redis."""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    def lpush(self, key: str, value: str) -> int:
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)
        return len(self.lists[key])

    def brpop(self, key: str, timeout: int = 5) -> tuple[str, str] | None:
        elementos = self.lists.get(key, [])
        if not elementos:
            return None
        return key, elementos.pop()

    def ping(self) -> bool:
        return True

    def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))


def test_redis_task_queue_cumple_protocolo() -> None:
    """DIP: RedisTaskQueue debe satisfacer TaskQueueProtocol."""
    assert isinstance(RedisTaskQueue(url="redis://localhost:6379/0"), TaskQueueProtocol)


def test_encolar_y_desencolar_exitoso() -> None:
    cola = RedisTaskQueue(url="redis://fake:6379/0")
    cola._client = FakeRedisClient()

    search_id = uuid4()
    assert cola.encolar(search_id) is True
    assert cola.tamano_cola() == 1

    desencolado = cola.desencolar(timeout=1)
    assert desencolado == search_id
    assert cola.tamano_cola() == 0


def test_desencolar_cola_vacia_retorna_none() -> None:
    cola = RedisTaskQueue(url="redis://fake:6379/0")
    cola._client = FakeRedisClient()

    assert cola.desencolar(timeout=1) is None


def test_encolar_captura_excepcion_sin_romper() -> None:
    cola = RedisTaskQueue(url="redis://fake:6379/0")
    mock_client = MagicMock()
    mock_client.lpush.side_effect = RuntimeError("Fallo de red simulado")
    cola._client = mock_client

    assert cola.encolar(uuid4()) is False


def test_worker_procesa_siguiente_tarea_exitosamente() -> None:
    cola = RedisTaskQueue(url="redis://fake:6379/0")
    cola._client = FakeRedisClient()

    search_id = uuid4()
    cola.encolar(search_id)

    mock_service = MagicMock()
    mock_db = MagicMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__enter__.return_value = mock_db

    procesado = procesar_siguiente_tarea(cola, mock_service, mock_session_factory, timeout=1)

    assert procesado == search_id
    mock_service.ejecutar_prospeccion_sync.assert_called_once_with(mock_db, search_id)


def test_worker_captura_error_en_prospeccion_sin_morir() -> None:
    cola = RedisTaskQueue(url="redis://fake:6379/0")
    cola._client = FakeRedisClient()

    search_id = uuid4()
    cola.encolar(search_id)

    mock_service = MagicMock()
    mock_service.ejecutar_prospeccion_sync.side_effect = ValueError("Error controlado")
    mock_session_factory = MagicMock()

    # No debe propagar la excepción
    procesado = procesar_siguiente_tarea(cola, mock_service, mock_session_factory, timeout=1)
    assert procesado == search_id
