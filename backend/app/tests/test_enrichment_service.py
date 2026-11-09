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


# --- Hardening de Seguridad Anti-SSRF y Límite DoS (AC-1 y AC-2) ---


def test_website_scraper_bloquea_urls_ssrf() -> None:
    """AC-1: bloquea localhost, IPs privadas, loopback, link-local y esquemas no HTTP."""
    scraper = WebsiteScraper()

    urls_maliciosas = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost.localdomain",
        "http://127.0.0.1",
        "http://127.0.0.1:5432",
        "http://[::1]",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "file:///etc/passwd",
        "ftp://servidor.com",
        "javascript:alert(1)",
    ]

    for url in urls_maliciosas:
        assert scraper._es_url_segura(url) is False, f"Debe bloquear SSRF para {url}"
        # La extracción devuelve lista vacía sin intentar conectar ni propagar excepciones
        assert scraper.extraer_emails(url) == []


def test_website_scraper_permite_urls_publicas_validas() -> None:
    """AC-1: URLs públicas con esquemas http/https son permitidas."""
    scraper = WebsiteScraper()
    assert scraper._es_url_segura("https://example.com") is True
    assert scraper._es_url_segura("http://google.com") is True


def test_website_scraper_bloquea_dns_rebinding_a_ip_privada(monkeypatch) -> None:
    """AC-1: bloquea dominios que resuelven a IPs privadas (DNS rebinding)."""
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("192.168.1.50", 80))],
    )
    scraper = WebsiteScraper()
    assert scraper._es_url_segura("http://dominio-aparentemente-publico.com") is False


def test_website_scraper_respeta_limite_max_bytes() -> None:
    """AC-2: el scraper trunca la lectura a max_bytes para evitar DoS por memoria."""
    # Email 1 está al inicio (dentro de los primeros 100 bytes)
    # Email 2 está después del byte 200
    html_inflado = (
        "<html><body><p>primer@negocio.com</p>"
        + ("x" * 500)
        + "<p>segundo@negocio.com</p></body></html>"
    )

    # Scraper con límite ajustado a 100 bytes
    scraper = WebsiteScraper(
        max_bytes=100,
        transport=lambda url: (html_inflado[:100], 200),
    )
    emails = scraper.extraer_emails("https://negocio.com")

    assert "primer@negocio.com" in emails
    assert "segundo@negocio.com" not in emails


def test_contact_enrichment_service_soporta_commit_flag(db_sqlite) -> None:
    """AC-4: enriquecer_contactos con commit=False no confirma la transacción."""
    from app.repositories.business_repo import BusinessRepository

    lead = Business(
        business_id=uuid4(),
        name="Clínica Dental Transaccional",
        website="https://dental-transaccional.com",
    )
    db_sqlite.add(lead)
    db_sqlite.commit()

    business_repo = BusinessRepository()
    mock_enricher = WebsiteScraper(
        transport=lambda url: ("<p>contacto@dental-transaccional.com</p>", 200)
    )
    service = ContactEnrichmentService(
        contact_repo=ContactRepository(),
        enricher=mock_enricher,
        business_repo=business_repo,
    )

    # Con commit=False no debe confirmar; podemos hacer rollback y verificar
    contactos = service.enriquecer_contactos(db_sqlite, lead.business_id, commit=False)
    assert len(contactos) == 1
    assert contactos[0].value == "contacto@dental-transaccional.com"

    db_sqlite.rollback()
    # Tras el rollback, el contacto no debe haberse persistido en la BD
    contactos_post_rollback = service.listar_contactos(db_sqlite, lead.business_id)
    assert contactos_post_rollback == []

