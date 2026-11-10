"""Pruebas E2E del pipeline de ingesta de extremo a extremo (issue #43).

Una busqueda ejecutada de punta a punta queda persistida y repetible sin
duplicados: rubro+ciudad -> discovery (negocios filtrados) -> resenas negativas
-> persistencia idempotente -> registro del resultado (estado, tiempos, error).
"""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.entities import Business, Review, Search
from app.repositories.business_repo import BusinessRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.search_repo import SearchRepository
from app.schemas.busqueda import SearchCreate
from app.schemas.discovery import Negocio
from app.schemas.resenas import Resena
from app.services.prospecting_service import ProspectingService


@pytest.fixture()
def db_sqlite():
    """Sesion directa de SQLite en memoria para pruebas de servicio."""
    motor = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(motor)
    db = fabrica()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(motor)
        motor.dispose()


class SerpFalso:
    """Discovery controlado: devuelve negocios o falla bajo demanda."""

    def __init__(self, negocios: list[Negocio] | None = None, fallar: bool = False):
        self.negocios = negocios or []
        self.fallar = fallar
        self.consultas: list[tuple[str, str]] = []

    def buscar_negocios(self, rubro: str, ciudad: str) -> list[Negocio]:
        self.consultas.append((rubro, ciudad))
        if self.fallar:
            raise RuntimeError("serpapi caido")
        return self.negocios


class MapsFalso:
    """Resenas negativas controladas: 5 por negocio, ya filtradas (contrato)."""

    def __init__(self) -> None:
        self.consultas: list[str] = []

    def obtener_resenas(self, consulta: str, cantidad: int = 5) -> list[Resena]:
        self.consultas.append(consulta)
        return [
            Resena(
                id=f"r{i}-{consulta}",
                estrellas=estrellas,
                texto=f"queja {i} de {consulta}",
                autor="cliente",
            )
            for i, estrellas in enumerate([1, 2, 2, 3, 3], start=1)
        ][:cantidad]


def _servicio(serp: SerpFalso, maps: MapsFalso) -> ProspectingService:
    return ProspectingService(
        search_repo=SearchRepository(),
        business_repo=BusinessRepository(),
        review_repo=ReviewRepository(),
        serp_client=serp,
        maps_client=maps,
    )


def _datos_entrada() -> SearchCreate:
    return SearchCreate(sector="cafeterias", city="Quito")


def test_pipeline_completo_persiste_el_resultado(db_sqlite) -> None:
    """AC: la busqueda termina COMPLETED con negocios, resenas y tiempos."""
    serp = SerpFalso(
        negocios=[
            Negocio(
                nombre="Cafe Central",
                rating=4.1,
                total_resenas=120,
                place_id="place-1",
            ),
            Negocio(
                nombre="Cafe Norte",
                rating=3.9,
                total_resenas=80,
                place_id="place-2",
            ),
        ]
    )
    maps = MapsFalso()
    servicio = _servicio(serp, maps)

    search = servicio.iniciar_busqueda(db_sqlite, _datos_entrada())
    assert search.status == "PENDING"

    servicio.ejecutar_prospeccion_sync(db_sqlite, search.search_id)

    registro = db_sqlite.get(Search, search.search_id)
    assert registro.status == "COMPLETED"
    assert registro.error_message is None
    assert registro.started_at is not None
    assert registro.finished_at is not None
    assert registro.finished_at >= registro.started_at

    assert servicio.contar_leads(db_sqlite, search.search_id) == 2
    assert db_sqlite.scalar(select(func.count()).select_from(Business)) == 2
    assert db_sqlite.scalar(select(func.count()).select_from(Review)) == 10

    assert serp.consultas == [("cafeterias", "Quito")]
    assert maps.consultas == ["Cafe Central Quito", "Cafe Norte Quito"]


def test_re_ejecutar_la_busqueda_no_duplica_nada(db_sqlite) -> None:
    """AC: repetir la ejecucion es idempotente, sin duplicar entidades."""
    serp = SerpFalso(
        negocios=[
            Negocio(
                nombre="Cafe Central",
                rating=4.1,
                total_resenas=120,
                place_id="place-1",
            )
        ]
    )
    maps = MapsFalso()
    servicio = _servicio(serp, maps)
    search = servicio.iniciar_busqueda(db_sqlite, _datos_entrada())

    servicio.ejecutar_prospeccion_sync(db_sqlite, search.search_id)
    servicio.ejecutar_prospeccion_sync(db_sqlite, search.search_id)

    assert db_sqlite.scalar(select(func.count()).select_from(Business)) == 1
    assert db_sqlite.scalar(select(func.count()).select_from(Review)) == 5
    assert servicio.contar_leads(db_sqlite, search.search_id) == 1

    registro = db_sqlite.get(Search, search.search_id)
    assert registro.status == "COMPLETED"
    assert registro.error_message is None


def test_fallo_de_discovery_registra_estado_error(db_sqlite) -> None:
    """AC: un fallo del discovery deja la busqueda FAILED con error y tiempos."""
    servicio = _servicio(SerpFalso(fallar=True), MapsFalso())
    search = servicio.iniciar_busqueda(db_sqlite, _datos_entrada())

    servicio.ejecutar_prospeccion_sync(db_sqlite, search.search_id)

    registro = db_sqlite.get(Search, search.search_id)
    assert registro.status == "FAILED"
    assert "serpapi caido" in (registro.error_message or "")
    assert registro.started_at is not None
    assert registro.finished_at is not None
