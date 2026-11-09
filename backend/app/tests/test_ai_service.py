"""Pruebas del servicio de análisis con IA, cold email y escudo anti-alucinación (RF4)."""

import json
import logging
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session, get_session_factory
from app.infrastructure.external.llm_client import LLMClient
from app.main import app
from app.models import (
    Base,
    Business,
    BusinessSource,
    Platform,
    Review,
)
from app.repositories.ai_repo import AIRepository
from app.schemas.ai import (
    CATALOGO_CATEGORIAS,
    CATEGORIA_FALLBACK,
    AIAnalysisResult,
)
from app.services.ai_service import AIService
from app.services.protocols import AIProviderProtocol


@pytest.fixture()
def db_sqlite():
    """Sesión directa de SQLite en memoria para pruebas de repositorio y servicio."""
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


@pytest.fixture()
def cliente_api_sqlite():
    """Cliente HTTP con base de datos SQLite en memoria."""
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


# --- DIP Protocol Compliance ---


def test_llm_client_satisface_ai_provider_protocol() -> None:
    """DIP: el cliente de inferencia concreta satisface la abstracción de servicios."""
    assert isinstance(LLMClient(), AIProviderProtocol)


# --- Escudo Anti-Alucinación (Pydantic Shield) ---


def test_escudo_anti_alucinacion_permite_categorias_controladas() -> None:
    """Las 6 categorías oficiales del catálogo son aceptadas exactamente."""
    for categoria in CATALOGO_CATEGORIAS:
        res = AIAnalysisResult(
            category=categoria,
            pain_points_summary="Problemas detectados",
            email_subject="Asunto de prueba",
            email_first_paragraph="Párrafo inicial",
        )
        assert res.category == categoria


def test_escudo_anti_alucinacion_case_insensitive() -> None:
    """Reconoce categorías válidas sin importar mayúsculas/minúsculas."""
    res = AIAnalysisResult(
        category="atención al cliente",
        pain_points_summary="Problemas",
        email_subject="Asunto",
        email_first_paragraph="Gancho",
    )
    assert res.category == "Atención al cliente"


def test_escudo_anti_alucinacion_mapea_a_otros_y_loguea_alerta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Categorías inventadas o no permitidas se mapean a 'Otros' con log de auditoría."""
    with caplog.at_level(logging.WARNING):
        res = AIAnalysisResult(
            category="Velocidad de internet inexistente",
            pain_points_summary="Problemas",
            email_subject="Asunto",
            email_first_paragraph="Gancho",
        )

    assert res.category == CATEGORIA_FALLBACK
    assert "[LLM_HALLUCINATION_DETECTED]" in caplog.text
    assert "Velocidad de internet inexistente" in caplog.text


def test_escudo_anti_alucinacion_valor_no_string_mapea_a_otros(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Entradas no string son interceptadas de forma segura hacia 'Otros'."""
    with caplog.at_level(logging.WARNING):
        res = AIAnalysisResult(
            category=12345,  # type: ignore[arg-type]
            pain_points_summary="Problemas",
            email_subject="Asunto",
            email_first_paragraph="Gancho",
        )

    assert res.category == CATEGORIA_FALLBACK
    assert "[LLM_HALLUCINATION_DETECTED]" in caplog.text


# --- Clasificador Heurístico Offline (LLMClient) ---


def test_llm_client_clasificacion_heuristica_categorias() -> None:
    """El clasificador heurístico asigna correctamente según palabras clave."""
    client = LLMClient(api_key=None)

    casos = [
        (["Pésima atención, el mesero fue muy grosero"], "Atención al cliente"),
        (["Mucha espera, tardaron 40 minutos en servir"], "Tiempos de espera"),
        (["Precios muy caros y cobro indebido en factura"], "Precios y facturación"),
        (["El baño estaba sucio y con mal olor"], "Higiene e instalaciones"),
        (["La comida fría y de muy mala calidad"], "Calidad del servicio"),
        (["No me convenció"], "Otros"),
    ]

    for resenas, cat_esperada in casos:
        resultado = client.analizar_resenas("Restaurante X", "Gastronomía", resenas)
        assert resultado.category == cat_esperada
        assert "Restaurante X" in resultado.email_subject
        assert "Gastronomía" in resultado.email_first_paragraph
        assert resultado.ai_model == "mock-heuristic-v1"


def test_llm_client_con_transporte_mock_exitoso() -> None:
    """Simula respuesta HTTP exitosa de API compatible con OpenAI."""
    payload_mock = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "category": "Tiempos de espera",
                        "pain_points_summary": "Demoras excesivas en atención",
                        "email_subject": "Propuesta para agilizar tiempos en Clínica Y",
                        "email_first_paragraph": "Hola Clínica Y, notamos demoras reportadas...",
                    })
                }
            }
        ]
    }

    def transport_mock(url: str, headers: dict[str, str], data: bytes) -> tuple[str, int]:
        assert "Bearer test-key" in headers["Authorization"]
        return json.dumps(payload_mock), 200

    client = LLMClient(api_key="test-key", transport=transport_mock)
    res = client.analizar_resenas("Clínica Y", "Salud", ["Demora de una hora"])

    assert res.category == "Tiempos de espera"
    assert res.pain_points_summary == "Demoras excesivas en atención"
    assert res.ai_model == "gpt-4o-mini"


def test_llm_client_transporte_con_error_recurre_a_heuristica() -> None:
    """Si el endpoint de IA falla (ej: 500), recurre transparentemente a la heurística."""

    def transport_error(url: str, headers: dict[str, str], data: bytes) -> tuple[str, int]:
        return "Internal Server Error", 500

    client = LLMClient(api_key="test-key", transport=transport_error)
    res = client.analizar_resenas("Bar Z", "Ocio", ["Pésima atención del personal"])

    assert res.category == "Atención al cliente"
    assert res.ai_model == "mock-heuristic-v1"


# --- Repositorio AIRepository ---


def test_ai_repository_ensure_categories_es_idempotente(db_sqlite) -> None:
    """Crea las 6 categorías maestras y una segunda ejecución no crea duplicados."""
    repo = AIRepository()
    cat_map1 = repo.ensure_categories(db_sqlite)
    assert set(cat_map1.keys()) == set(CATALOGO_CATEGORIAS)

    total_inicial = len(cat_map1)
    cat_map2 = repo.ensure_categories(db_sqlite)
    assert len(cat_map2) == total_inicial


def test_ai_repository_upsert_analysis_es_idempotente(db_sqlite) -> None:
    """Inserta y luego actualiza un análisis para el mismo negocio sin duplicar."""
    repo = AIRepository()
    categorias = repo.ensure_categories(db_sqlite)
    cat_atencion = categorias["Atención al cliente"]
    cat_espera = categorias["Tiempos de espera"]

    negocio_id = uuid4()
    negocio = Business(business_id=negocio_id, name="Prueba Idempotencia")
    db_sqlite.add(negocio)
    db_sqlite.commit()

    # Inserción inicial
    analisis1 = repo.upsert_analysis(
        db=db_sqlite,
        business_id=negocio_id,
        problem_category_id=cat_atencion.problem_category_id,
        pain_points_summary="Problemas de atención",
        email_subject="Asunto 1",
        email_first_paragraph="Párrafo 1",
        ai_model="mock-1",
    )
    db_sqlite.commit()
    assert analisis1.problem_category_id == cat_atencion.problem_category_id

    # Actualización sobre el mismo negocio
    analisis2 = repo.upsert_analysis(
        db=db_sqlite,
        business_id=negocio_id,
        problem_category_id=cat_espera.problem_category_id,
        pain_points_summary="Problemas de espera actualizados",
        email_subject="Asunto 2",
        email_first_paragraph="Párrafo 2",
        ai_model="mock-2",
    )
    db_sqlite.commit()

    assert analisis2.analysis_id == analisis1.analysis_id
    assert analisis2.problem_category_id == cat_espera.problem_category_id
    assert analisis2.pain_points_summary == "Problemas de espera actualizados"


# --- Servicio AIService ---


def test_ai_service_analizar_negocio_end_to_end(db_sqlite) -> None:
    """Orquesta la extracción de reseñas negativas, categorización y persistencia."""
    repo = AIRepository()
    provider = LLMClient()
    service = AIService(ai_repo=repo, ai_provider=provider)

    business = Business(
        business_id=uuid4(),
        name="Café Central",
        sector="Cafeterías",
        city="Buenos Aires",
    )
    platform = Platform(name="Google Maps")
    db_sqlite.add_all([business, platform])
    db_sqlite.flush()

    source = BusinessSource(
        business_id=business.business_id,
        platform_id=platform.platform_id,
        external_id="place-cafe-123",
        rating=Decimal("2.9"),
        total_reviews=15,
    )
    db_sqlite.add(source)
    db_sqlite.flush()

    review = Review(
        business_source_id=source.business_source_id,
        external_id="rev-1",
        author="Cliente Descontento",
        rating=1,
        content="Muy mala atención de los meseros, nos ignoraron por completo.",
    )
    db_sqlite.add(review)
    db_sqlite.commit()

    analisis = service.analizar_negocio(db_sqlite, business.business_id)

    assert analisis is not None
    assert analisis.business_id == business.business_id
    assert analisis.problem_category.name == "Atención al cliente"
    assert "atención al cliente" in analisis.email_subject.lower()
    assert "Café Central" in analisis.email_subject


def test_ai_service_negocio_inexistente_retorna_none(db_sqlite) -> None:
    """Si el negocio no existe en la base de datos, devuelve None."""
    service = AIService(ai_repo=AIRepository(), ai_provider=LLMClient())
    assert service.analizar_negocio(db_sqlite, uuid4()) is None


# --- Endpoints API Leads con IA ---


def test_api_analisis_ia_lifecycle(cliente_api_sqlite) -> None:
    """Verifica GET 404 inicial, POST para generar y GET 200 posterior."""
    cliente, fabrica = cliente_api_sqlite

    with fabrica() as db:
        platform = Platform(name="Google Maps")
        business = Business(
            name="Veterinaria San Roque",
            sector="Veterinarias",
            city="Montevideo",
        )
        db.add_all([platform, business])
        db.flush()
        source = BusinessSource(
            business_id=business.business_id,
            platform_id=platform.platform_id,
            external_id="vet-123",
            rating=Decimal("2.5"),
            total_reviews=20,
        )
        db.add(source)
        db.flush()
        db.add(
            Review(
                business_source_id=source.business_source_id,
                external_id="rev-vet-1",
                rating=2,
                content="Los precios son excesivos y nos cobraron de más en la factura.",
            )
        )
        db.commit()
        lead_id = str(business.business_id)

    # 1. GET inicial sin análisis previo da 404
    resp_get_inicial = cliente.get(f"/api/v1/leads/{lead_id}/ai-analysis")
    assert resp_get_inicial.status_code == 404

    # 2. POST genera el análisis de IA
    resp_post = cliente.post(f"/api/v1/leads/{lead_id}/ai-analysis")
    assert resp_post.status_code == 200
    cuerpo_post = resp_post.json()
    assert cuerpo_post["business_id"] == lead_id
    assert cuerpo_post["category"] == "Precios y facturación"
    assert "precios y facturación" in cuerpo_post["email_subject"].lower()
    assert cuerpo_post["email_first_paragraph"] is not None

    # 3. GET posterior devuelve el análisis persistido
    resp_get_final = cliente.get(f"/api/v1/leads/{lead_id}/ai-analysis")
    assert resp_get_final.status_code == 200
    assert resp_get_final.json()["analysis_id"] == cuerpo_post["analysis_id"]

    # 4. Listado de leads expone el análisis integrado en LeadResponse
    resp_leads = cliente.get("/api/v1/leads")
    assert resp_leads.status_code == 200
    leads = resp_leads.json()["items"]
    lead_encontrado = next(item for item in leads if item["business_id"] == lead_id)
    assert lead_encontrado["ai_analysis"] is not None
    assert lead_encontrado["ai_analysis"]["category"] == "Precios y facturación"


def test_api_analisis_ia_lead_inexistente_da_404(cliente_api_sqlite) -> None:
    """Peticiones a leads que no existen devuelven 404."""
    cliente, _ = cliente_api_sqlite
    random_id = uuid4()
    assert cliente.get(f"/api/v1/leads/{random_id}/ai-analysis").status_code == 404
    assert cliente.post(f"/api/v1/leads/{random_id}/ai-analysis").status_code == 404


def test_ai_service_soporta_commit_flag(db_sqlite) -> None:
    """AC-4: analizar_negocio con commit=False no confirma la transacción."""
    from app.repositories.business_repo import BusinessRepository

    lead = Business(
        business_id=uuid4(),
        name="Clínica IA Transaccional",
        sector="Salud",
    )
    db_sqlite.add(lead)
    db_sqlite.commit()

    service = AIService(
        ai_repo=AIRepository(),
        ai_provider=LLMClient(),
        business_repo=BusinessRepository(),
    )

    analisis = service.analizar_negocio(db_sqlite, lead.business_id, commit=False)
    assert analisis is not None

    db_sqlite.rollback()
    # Tras el rollback, el análisis no debe estar persistido en la BD
    recuperado = service.obtener_analisis(db_sqlite, lead.business_id)
    assert recuperado is None

