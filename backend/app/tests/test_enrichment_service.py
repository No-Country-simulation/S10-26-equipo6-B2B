"""Pruebas del servicio de enriquecimiento secundario de contactos web (RF3)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session, get_session_factory
from app.infrastructure.external.website_scraper import WebsiteScraper
from app.main import app
from app.models import Base, Business, Contact
from app.repositories.contact_repo import ContactRepository
from app.services.enrichment_service import ContactEnrichmentService
from app.services.protocols import ContactEnricherProtocol


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


def test_website_scraper_satisface_contact_enricher_protocol() -> None:
    """DIP: el scraper concreto satisface la abstracción de servicios."""
    assert isinstance(WebsiteScraper(), ContactEnricherProtocol)


# --- Scraper e Inferencia de Correos (Regex y Filtrado) ---


def test_website_scraper_extrae_y_normaliza_emails() -> None:
    """Extrae emails válidos, normaliza a minúsculas y deduplica."""
    html = """
    <html>
      <body>
        <h1>Contacto</h1>
        <p>Escríbenos a <a href="mailto:INFO@dental.com">INFO@dental.com</a></p>
        <p>O al soporte: citas@dental.com</p>
        <p>Duplicado: info@dental.com</p>
      </body>
    </html>
    """
    scraper = WebsiteScraper(transport=lambda url: (html, 200))
    emails = scraper.extraer_emails("https://dental.com")

    assert emails == ["info@dental.com", "citas@dental.com"]


def test_website_scraper_descarta_falsos_positivos() -> None:
    """Ignora archivos estáticos (.png, .svg) y dominios plantilla (example.com)."""
    html = """
    <div>
      <img src="icono@2x.png" />
      <img src="logo@3x.svg" />
      <p>Contacto de ejemplo: test@example.com</p>
      <p>Otro falso: user@wixpress.com</p>
      <p>Correo real: reservas@restaurante.com</p>
    </div>
    """
    scraper = WebsiteScraper(transport=lambda url: (html, 200))
    emails = scraper.extraer_emails("https://restaurante.com")

    assert emails == ["reservas@restaurante.com"]


def test_website_scraper_navega_subpaginas_si_home_no_tiene_emails() -> None:
    """Si la home no tiene correos, busca en /contacto."""

    def transport_mock(url: str) -> tuple[str, int]:
        if url.endswith("/contacto"):
            return "<footer>Envíanos un mail a contacto@empresa.com</footer>", 200
        return "<html><body>Home sin correos</body></html>", 200

    scraper = WebsiteScraper(transport=transport_mock)
    emails = scraper.extraer_emails("https://empresa.com")

    assert emails == ["contacto@empresa.com"]


def test_website_scraper_maneja_errores_red_sin_excepcion() -> None:
    """Sitios caídos o respuestas 404/500 no rompen la ejecución; retornan []."""

    def transport_error(url: str) -> tuple[str, int]:
        return "Not Found", 404

    scraper = WebsiteScraper(transport=transport_error)
    assert scraper.extraer_emails("https://sitio-caido.com") == []
    assert scraper.extraer_emails("") == []


# --- Repositorio ContactRepository ---


def test_contact_repository_save_contacts_es_idempotente(db_sqlite) -> None:
    """Guarda contactos y una segunda llamada no genera duplicados."""
    repo = ContactRepository()
    lead_id = uuid4()
    lead = Business(business_id=lead_id, name="Lead Test")
    db_sqlite.add(lead)
    db_sqlite.commit()

    # Primera inserción
    guardados1 = repo.save_contacts(
        db_sqlite,
        lead_id,
        ["info@test.com", "admin@test.com"],
    )
    db_sqlite.commit()
    assert len(guardados1) == 2

    # Segunda inserción con uno existente y uno nuevo
    guardados2 = repo.save_contacts(
        db_sqlite,
        lead_id,
        ["INFO@test.com", "nuevo@test.com"],
    )
    db_sqlite.commit()
    assert len(guardados2) == 1
    assert guardados2[0].value == "nuevo@test.com"

    todos = repo.list_by_business(db_sqlite, lead_id)
    assert len(todos) == 3
    assert {c.value for c in todos} == {"info@test.com", "admin@test.com", "nuevo@test.com"}


# --- Servicio ContactEnrichmentService ---


def test_enrichment_service_enriquecer_contactos_end_to_end(db_sqlite) -> None:
    """Orquesta la extracción web y persistencia de contactos en base de datos."""
    lead = Business(
        business_id=uuid4(),
        name="Clínica Dental Sonrisas",
        website="https://sonrisas.com",
    )
    db_sqlite.add(lead)
    db_sqlite.commit()

    html = "<p>Pide tu cita a recepcion@sonrisas.com</p>"
    scraper = WebsiteScraper(transport=lambda url: (html, 200))
    service = ContactEnrichmentService(contact_repo=ContactRepository(), enricher=scraper)

    contactos = service.enriquecer_contactos(db_sqlite, lead.business_id)

    assert len(contactos) == 1
    assert contactos[0].value == "recepcion@sonrisas.com"
    assert contactos[0].contact_type == "EMAIL"
    assert contactos[0].source == "BUSINESS_WEBSITE"


def test_enrichment_service_sin_website_retorna_existentes(db_sqlite) -> None:
    """Si el lead no tiene website, retorna los contactos actuales sin fallar."""
    lead = Business(
        business_id=uuid4(),
        name="Taller Sin Web",
        website=None,
    )
    db_sqlite.add(lead)
    db_sqlite.commit()

    service = ContactEnrichmentService(
        contact_repo=ContactRepository(),
        enricher=WebsiteScraper(),
    )
    contactos = service.enriquecer_contactos(db_sqlite, lead.business_id)
    assert contactos == []


# --- Endpoints REST API Leads con Contactos ---


def test_api_contactos_lifecycle(cliente_api_sqlite) -> None:
    """Verifica GET /contacts y POST /enrich-contacts en la API."""
    cliente, fabrica = cliente_api_sqlite

    with fabrica() as db:
        lead = Business(
            name="Restaurante La Parrilla",
            sector="Restaurantes",
            city="Santiago",
            website="https://laparrilla.cl",
        )
        db.add(lead)
        db.flush()
        lead_id = str(lead.business_id)
        db.add(
            Contact(
                business_id=lead.business_id,
                contact_type="EMAIL",
                value="info@laparrilla.cl",
                source="BUSINESS_WEBSITE",
            )
        )
        db.commit()

    # 1. GET /contacts devuelve el contacto existente
    resp_get = cliente.get(f"/api/v1/leads/{lead_id}/contacts")
    assert resp_get.status_code == 200
    cuerpo_get = resp_get.json()
    assert len(cuerpo_get) == 1
    assert cuerpo_get[0]["value"] == "info@laparrilla.cl"

    # 2. GET /leads expone email principal y contacts
    resp_leads = cliente.get("/api/v1/leads")
    assert resp_leads.status_code == 200
    leads = resp_leads.json()["items"]
    lead_dto = next(item for item in leads if item["business_id"] == lead_id)
    assert lead_dto["email"] == "info@laparrilla.cl"
    assert len(lead_dto["contacts"]) == 1
    assert lead_dto["contacts"][0]["value"] == "info@laparrilla.cl"
