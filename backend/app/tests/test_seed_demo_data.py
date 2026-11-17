"""Pruebas unitarias para el script de población de datos de demostración."""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.api.deps import get_db_session, get_session_factory
from app.infrastructure.database.seed_demo import seed_demo_data
from app.infrastructure.database.session import seed_catalogs
from app.main import app
from app.models import (
    AIAnalysis,
    Base,
    Business,
    BusinessSource,
    Contact,
    Review,
    Search,
    SearchBusiness,
)


@pytest.fixture()
def db_sqlite():
    """Sesión de prueba aislada con SQLite en memoria."""
    motor = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(motor)

    with fabrica() as db:
        seed_catalogs(db)
        yield db

    Base.metadata.drop_all(motor)
    motor.dispose()


@pytest.fixture()
def cliente_con_seed():
    """TestClient de FastAPI con base de datos sembrada con 200 leads."""
    motor = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(motor)

    with fabrica() as db:
        seed_demo_data(db, max_leads=200)

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
        yield cliente
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(motor)
        motor.dispose()


def test_seed_demo_data_puebla_200_leads_completos(db_sqlite) -> None:
    """Verifica que se generen exactamente 200 leads con sus 9 entidades relacionadas."""
    resultado = seed_demo_data(db_sqlite, max_leads=200)

    assert resultado["creados"] == 200
    assert resultado["existentes"] == 0

    total_businesses = db_sqlite.scalar(select(func.count(Business.business_id)))
    assert total_businesses == 200

    total_sources = db_sqlite.scalar(select(func.count(BusinessSource.business_source_id)))
    assert total_sources == 200

    total_analyses = db_sqlite.scalar(select(func.count(AIAnalysis.analysis_id)))
    assert total_analyses == 200

    total_contacts = db_sqlite.scalar(select(func.count(Contact.contact_id)))
    assert total_contacts == 200

    total_reviews = db_sqlite.scalar(select(func.count(Review.review_id)))
    assert total_reviews >= 600

    total_searches = db_sqlite.scalar(select(func.count(Search.search_id)))
    assert total_searches >= 8

    total_links = db_sqlite.scalar(select(func.count(SearchBusiness.business_id)))
    assert total_links == 200


def test_seed_demo_data_cumple_criterios_de_calificacion(db_sqlite) -> None:
    """Comprueba que todos los leads califiquen para el MVP (< 3.5 estrellas y > 10 reseñas)."""
    seed_demo_data(db_sqlite, max_leads=50)

    sources = db_sqlite.scalars(select(BusinessSource)).all()
    for source in sources:
        assert float(source.rating) <= 3.5
        assert float(source.rating) >= 2.0
        assert source.total_reviews >= 10

    # Comprueba que las reseñas asociadas sean negativas (rating <= 3)
    reviews = db_sqlite.scalars(select(Review)).all()
    for rev in reviews:
        assert rev.rating <= 3
        assert len(rev.content) > 10


def test_seed_demo_data_es_idempotente(db_sqlite) -> None:
    """Ejecutar el seeding dos veces no debe duplicar registros ni lanzar errores."""
    primera_vez = seed_demo_data(db_sqlite, max_leads=30)
    assert primera_vez["creados"] == 30
    assert primera_vez["existentes"] == 0

    segunda_vez = seed_demo_data(db_sqlite, max_leads=30)
    assert segunda_vez["creados"] == 0
    assert segunda_vez["existentes"] == 30

    total_businesses = db_sqlite.scalar(select(func.count(Business.business_id)))
    assert total_businesses == 30


def test_seed_demo_data_distribuye_estados_de_crm(db_sqlite) -> None:
    """Verifica que el dataset contenga variedad de estados (NEW, CONTACTED, DISCARDED)."""
    seed_demo_data(db_sqlite, max_leads=100)

    estados = set(db_sqlite.scalars(select(Business.lead_status)).all())
    assert "NEW" in estados
    assert "CONTACTED" in estados
    assert "DISCARDED" in estados

    contactados = db_sqlite.scalars(
        select(Business).where(Business.lead_status == "CONTACTED")
    ).all()
    assert len(contactados) > 0
    for lead in contactados:
        assert lead.contacted_at is not None


def test_api_recupera_leads_sembrados(cliente_con_seed) -> None:
    """Verifica que la API REST devuelva los leads sembrados con formato PaginatedResponse."""
    respuesta = cliente_con_seed.get("/api/v1/leads?page=1&limit=50")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 200
    assert datos["page"] == 1
    assert datos["page_size"] == 50
    assert len(datos["items"]) == 50
    assert datos["has_next"] is True

    primer_lead = datos["items"][0]
    assert "business_id" in primer_lead
    assert "name" in primer_lead
    assert primer_lead["rating"] <= 3.5
    assert primer_lead["total_reviews"] >= 10
    assert primer_lead["ai_analysis"] is not None
    assert primer_lead["ai_analysis"]["email_subject"] is not None
    assert len(primer_lead["contacts"]) >= 1
