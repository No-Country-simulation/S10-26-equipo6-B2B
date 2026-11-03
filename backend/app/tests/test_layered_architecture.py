"""Pruebas de la arquitectura por capas: modelos, paginación y routers."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import UniqueConstraint, Uuid, create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
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
