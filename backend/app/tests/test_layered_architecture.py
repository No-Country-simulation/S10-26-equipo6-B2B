"""Pruebas de la arquitectura por capas: modelos, paginación y routers."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import UniqueConstraint, Uuid, create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session, get_session_factory
from app.infrastructure.external.google_maps_client import GoogleMapsClient
from app.infrastructure.external.llm_client import LLMClient
from app.infrastructure.external.serpapi_client import SerpApiDiscovery
from app.main import app
from app.models import (
    AIAnalysis,
    Base,
    Business,
    BusinessSource,
    Contact,
    Platform,
    ProblemCategory,
    Review,
    Search,
    SearchBusiness,
)
from app.repositories.business_repo import BusinessRepository
from app.schemas.common import PaginatedResponse
from app.schemas.discovery import Negocio
from app.services.protocols import (
    AIProviderProtocol,
    DiscoveryProviderProtocol,
    ReviewProviderProtocol,
)

TABLAS_ESPERADAS = {
    "ai_analysis",
    "business",
    "business_source",
    "contact",
    "platform",
    "problem_category",
    "review",
    "search",
    "search_business",
}


def test_el_erd_expone_las_nueve_tablas() -> None:
    assert set(Base.metadata.tables) == TABLAS_ESPERADAS


def test_instancia_las_nueve_entidades() -> None:
    business_id = uuid4()
    source_id = uuid4()

    platform = Platform(platform_id=1, name="Google Maps")
    search = Search(search_id=uuid4(), sector="clínicas dentales", city="Bogotá")
    business = Business(business_id=business_id, name="Clínica Dental Ejemplo")
    search_business = SearchBusiness(
        search_id=search.search_id,
        business_id=business_id,
    )
    source = BusinessSource(
        business_source_id=source_id,
        business_id=business_id,
        platform_id=platform.platform_id,
        external_id="ChIJ-test",
        rating=Decimal("3.1"),
        total_reviews=12,
    )
    review = Review(
        review_id=uuid4(),
        business_source_id=source_id,
        external_id="review-1",
        rating=1,
        content="Mala atención",
    )
    category = ProblemCategory(problem_category_id=1, name="Atención al cliente")
    analysis = AIAnalysis(
        analysis_id=uuid4(),
        business_id=business_id,
        problem_category_id=category.problem_category_id,
    )
    contact = Contact(
        contact_id=uuid4(),
        business_id=business_id,
        contact_type="EMAIL",
        value="contacto@dental.com",
        source="BUSINESS_WEBSITE",
    )

    assert platform.name == "Google Maps"
    assert search.sector == "clínicas dentales"
    assert business.name == "Clínica Dental Ejemplo"
    assert search_business.search_id == search.search_id
    assert source.rating == Decimal("3.1")
    assert review.rating == 1
    assert category.name == "Atención al cliente"
    assert analysis.business_id == business_id
    assert contact.value == "contacto@dental.com"


def test_claves_primarias_y_restricciones_del_erd() -> None:
    assert list(Search.__table__.primary_key.columns.keys()) == ["search_id"]
    assert list(Business.__table__.primary_key.columns.keys()) == ["business_id"]
    assert set(SearchBusiness.__table__.primary_key.columns.keys()) == {
        "search_id",
        "business_id",
    }

    uniques_source = {
        constraint.name
        for constraint in BusinessSource.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    uniques_review = {
        constraint.name
        for constraint in Review.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_business_source_platform_external" in uniques_source
    assert "uq_review_source_external" in uniques_review
    assert AIAnalysis.__table__.c.business_id.unique is True


def test_tipos_de_columnas_clave() -> None:
    assert isinstance(Search.__table__.c.search_id.type, Uuid)
    assert isinstance(Business.__table__.c.business_id.type, Uuid)
    assert Business.__table__.c.name.type.length == 150
    assert Search.__table__.c.max_rating.type.precision == 2
    assert Search.__table__.c.max_rating.type.scale == 1


def test_paginated_response_calcula_metadatos() -> None:
    respuesta = PaginatedResponse[int](
        items=[1, 2],
        total=25,
        page=2,
        page_size=10,
    )

    assert respuesta.total_pages == 3
    assert respuesta.has_next is True


def test_paginated_response_ultima_pagina() -> None:
    respuesta = PaginatedResponse[int](
        items=[21, 22],
        total=22,
        page=3,
        page_size=10,
    )

    assert respuesta.total_pages == 3
    assert respuesta.has_next is False


def test_paginated_response_vacia() -> None:
    respuesta = PaginatedResponse[int](
        items=[],
        total=0,
        page=1,
        page_size=20,
    )

    assert respuesta.total_pages == 0
    assert respuesta.has_next is False


@pytest.fixture()
def cliente_sqlite():
    """Cliente HTTP con SQLite en memoria, sin depender de PostgreSQL."""
    motor = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(motor)

    def override_get_db():
        db = fabrica()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: fabrica
    cliente = TestClient(app)
    try:
        yield cliente, fabrica
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(motor)
        motor.dispose()


def _sembrar_lead(fabrica) -> str:
    with fabrica() as db:
        platform = Platform(name="Google Maps")
        business = Business(
            name="Clínica Dental Ejemplo",
            sector="clínicas dentales",
            city="Bogotá",
        )
        db.add_all([platform, business])
        db.flush()
        db.add(
            BusinessSource(
                business_id=business.business_id,
                platform_id=platform.platform_id,
                external_id="ChIJ-test",
                rating=Decimal("3.1"),
                total_reviews=12,
                last_scraped_at=datetime(2026, 10, 20, tzinfo=UTC),
            )
        )
        db.commit()
        return str(business.business_id)


def test_upsert_from_discovery_es_idempotente(cliente_sqlite) -> None:
    _, fabrica = cliente_sqlite
    with fabrica() as db:
        repositorio = BusinessRepository()
        platform = repositorio.ensure_platform(db)
        negocio = Negocio(
            nombre="Clínica Idempotente",
            rating=3.2,
            total_resenas=20,
            place_id="ChIJ-idempotente",
        )

        primero = repositorio.upsert_from_discovery(db, negocio, platform.platform_id)
        db.commit()
        segundo = repositorio.upsert_from_discovery(
            db,
            negocio.model_copy(update={"rating": 2.9, "total_resenas": 25}),
            platform.platform_id,
        )
        db.commit()

        assert segundo.business_source_id == primero.business_source_id
        assert segundo.rating == Decimal("2.9")
        assert segundo.total_reviews == 25
        assert db.scalar(select(func.count()).select_from(BusinessSource)) == 1


def test_health(cliente_sqlite) -> None:
    cliente, _ = cliente_sqlite

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"


def test_post_busqueda_con_payload_invalido_da_422(cliente_sqlite) -> None:
    cliente, _ = cliente_sqlite

    respuesta = cliente.post(
        "/api/v1/busquedas",
        json={"sector": "clínicas dentales"},
    )

    assert respuesta.status_code == 422


def test_post_busqueda_valida_responde_202_y_pending(cliente_sqlite, monkeypatch) -> None:
    cliente, _ = cliente_sqlite

    # Evita llamadas de red síncronas/asíncronas en el test unitario del contrato
    monkeypatch.setattr(
        "app.services.prospecting_service.ProspectingService.ejecutar_prospeccion_sync",
        lambda self, db, search_id: None,
    )

    respuesta = cliente.post(
        "/api/v1/busquedas",
        json={
            "sector": "clínicas dentales",
            "city": "Bogotá",
            "max_rating": 3.5,
            "min_reviews": 10,
        },
    )

    assert respuesta.status_code == 202
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "PENDING"
    assert cuerpo["sector"] == "clínicas dentales"
    assert cuerpo["city"] == "Bogotá"
    assert "search_id" in cuerpo


def test_get_busqueda_existente_devuelve_status(cliente_sqlite) -> None:
    cliente, fabrica = cliente_sqlite
    with fabrica() as db:
        search = Search(
            sector="restaurantes",
            city="Lima",
            status="IN_PROGRESS",
        )
        db.add(search)
        db.commit()
        search_id = str(search.search_id)

    respuesta = cliente.get(f"/api/v1/busquedas/{search_id}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["search_id"] == search_id
    assert cuerpo["status"] == "IN_PROGRESS"
    assert cuerpo["leads_encontrados"] == 0


def test_get_busqueda_inexistente_responde_404(cliente_sqlite) -> None:
    cliente, _ = cliente_sqlite
    random_id = uuid4()

    respuesta = cliente.get(f"/api/v1/busquedas/{random_id}")

    assert respuesta.status_code == 404
    assert "no encontrada" in respuesta.json()["detail"]


def test_get_leads_devuelve_paginated_response(cliente_sqlite) -> None:
    cliente, fabrica = cliente_sqlite
    business_id = _sembrar_lead(fabrica)

    respuesta = cliente.get("/api/v1/leads?page=1&limit=10")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {
        "items",
        "total",
        "page",
        "page_size",
        "total_pages",
        "has_next",
    }
    assert cuerpo["total"] == 1
    assert cuerpo["page"] == 1
    assert cuerpo["page_size"] == 10
    assert cuerpo["total_pages"] == 1
    assert cuerpo["has_next"] is False

    lead = cuerpo["items"][0]
    assert lead["business_id"] == business_id
    assert lead["name"] == "Clínica Dental Ejemplo"
    assert lead["rating"] == 3.1
    assert lead["total_reviews"] == 12
    assert lead["lead_status"] == "NEW"


def test_get_leads_vacio_tambien_respeta_el_contrato(cliente_sqlite) -> None:
    cliente, _ = cliente_sqlite

    respuesta = cliente.get("/api/v1/leads?page=1&limit=10")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 10,
        "total_pages": 0,
        "has_next": False,
    }


def test_patch_lead_status_actualiza_el_estado(cliente_sqlite) -> None:
    cliente, fabrica = cliente_sqlite
    business_id = _sembrar_lead(fabrica)

    respuesta = cliente.patch(
        f"/api/v1/leads/{business_id}/status",
        json={"lead_status": "CONTACTED"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["lead_status"] == "CONTACTED"


def test_patch_lead_status_invalido_da_422(cliente_sqlite) -> None:
    cliente, fabrica = cliente_sqlite
    business_id = _sembrar_lead(fabrica)

    respuesta = cliente.patch(
        f"/api/v1/leads/{business_id}/status",
        json={"lead_status": "INVENTADO"},
    )

    assert respuesta.status_code == 422


# --- Cumplimiento S.O.L.I.D. -------------------------------------------------


def test_serpapi_discovery_implementa_el_protocolo_de_discovery() -> None:
    """DIP: el cliente concreto satisface la abstracción de la capa de servicios."""
    assert isinstance(SerpApiDiscovery(api_key="x"), DiscoveryProviderProtocol)


def test_google_maps_client_implementa_el_protocolo_de_resenas() -> None:
    """DIP: el adaptador de Maps satisface ``ReviewProviderProtocol``."""
    assert isinstance(GoogleMapsClient(), ReviewProviderProtocol)


def test_llm_client_implementa_el_protocolo_de_ia() -> None:
    """DIP: el cliente de IA satisface ``AIProviderProtocol``."""
    assert isinstance(LLMClient(), AIProviderProtocol)



def test_cli_etl_resenas_delega_en_google_maps_client() -> None:
    """Soporte QA: ``app.etl.resenas`` es un shim CLI que delega en infrastructure."""
    from app.etl import resenas
    from app.infrastructure.external import google_maps_client

    assert hasattr(resenas, "correr_smoke_test")
    assert hasattr(resenas, "main")
    assert resenas.obtener_resenas is google_maps_client.obtener_resenas


def test_flujo_unidireccional_estricto_de_capas() -> None:
    """Layered Monolith: ninguna capa inferior debe importar de capas superiores.

    Reglas formales (AGENTS.md y backend-layered-architecture.md):
    1. infrastructure/ NUNCA importa de app.services ni app.api.
    2. models/ y repositories/ NUNCA importan de app.services ni app.api.
    3. services/ NUNCA importa de app.api.
    """
    import ast
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[1]

    def _extraer_modulos_importados(archivo: Path) -> list[str]:
        contenido = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(contenido, filename=str(archivo))
        modulos: list[str] = []
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    modulos.append(alias.name)
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos.append(nodo.module)
        return modulos

    # 1. infrastructure no debe importar de services ni de api
    infra_dir = app_dir / "infrastructure"
    for py_file in infra_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        rel = py_file.relative_to(app_dir)
        for mod in _extraer_modulos_importados(py_file):
            assert not (mod == "app.services" or mod.startswith("app.services.")), (
                f"Violación de capas: {rel} en infrastructure importa de '{mod}'"
            )
            assert not (mod == "app.api" or mod.startswith("app.api.")), (
                f"Violación de capas: {rel} en infrastructure importa de '{mod}'"
            )

    # 2. models y repositories no deben importar de services ni de api
    for capa in ("models", "repositories"):
        capa_dir = app_dir / capa
        for py_file in capa_dir.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            rel = py_file.relative_to(app_dir)
            for mod in _extraer_modulos_importados(py_file):
                assert not (mod == "app.services" or mod.startswith("app.services.")), (
                    f"Violación de capas: {rel} en {capa} importa de '{mod}'"
                )
                assert not (mod == "app.api" or mod.startswith("app.api.")), (
                    f"Violación de capas: {rel} en {capa} importa de '{mod}'"
                )

    # 3. services no debe importar de api
    services_dir = app_dir / "services"
    for py_file in services_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        rel = py_file.relative_to(app_dir)
        for mod in _extraer_modulos_importados(py_file):
            assert not (mod == "app.api" or mod.startswith("app.api.")), (
                f"Violación de capas: {rel} en services importa de '{mod}'"
            )
