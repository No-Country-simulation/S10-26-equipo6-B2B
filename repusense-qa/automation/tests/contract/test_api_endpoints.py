"""Pruebas de endpoints REST para la API de RepuSense (Issue #25 / Tarea 4).

Cubre los 4 endpoints de la API v1:
- POST /api/v1/busquedas (Crear búsqueda de prospección)
- GET /api/v1/busquedas/{id} (Consultar estado)
- GET /api/v1/leads (Listar y filtrar leads paginados)
- PATCH /api/v1/leads/{id}/status (Actualizar estado comercial)

Utiliza SQLite en memoria para pruebas rápidas, aisladas y sin dependencias externas.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from app.api.deps import get_db_session, get_session_factory
from app.main import app
from app.models import Base, Business, BusinessSource, Platform
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def cliente_api():
    """Provee un cliente de pruebas conectado a una base de datos SQLite en memoria limpia."""
    motor = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(motor)

    def override_db():
        db = fabrica()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_session_factory] = lambda: fabrica
    cliente = TestClient(app)

    try:
        yield cliente, fabrica
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(motor)
        motor.dispose()


# ---------------------------------------------------------------------------
# 1. Pruebas para POST /api/v1/busquedas
# ---------------------------------------------------------------------------


def test_tc_api_busq_01_crear_busqueda_correcta(cliente_api) -> None:
    """Verifica que enviar sector y ciudad válidos inicie la búsqueda con estado PENDING."""
    cliente, _ = cliente_api
    payload = {"sector": "restaurantes", "city": "Medellin"}

    respuesta = cliente.post("/api/v1/busquedas", json=payload)

    assert respuesta.status_code == 202
    datos = respuesta.json()
    assert datos["status"] == "PENDING"
    assert datos["sector"] == "restaurantes"
    assert datos["city"] == "Medellin"
    assert UUID(datos["search_id"])


def test_tc_api_busq_02_limite_calificacion_invalida_superior(cliente_api) -> None:
    """Verifica que se rechacen calificaciones mayores a 5.0 estrellas."""
    cliente, _ = cliente_api
    payload = {"sector": "hoteles", "city": "Quito", "max_rating": 5.1}

    respuesta = cliente.post("/api/v1/busquedas", json=payload)

    assert respuesta.status_code == 422


def test_tc_api_busq_03_limite_calificacion_invalida_negativa(cliente_api) -> None:
    """Verifica que se rechacen calificaciones menores a 0 estrellas."""
    cliente, _ = cliente_api
    payload = {"sector": "hoteles", "city": "Quito", "max_rating": -0.5}

    respuesta = cliente.post("/api/v1/busquedas", json=payload)

    assert respuesta.status_code == 422


def test_tc_api_busq_04_limite_minimo_resenas_negativo(cliente_api) -> None:
    """Verifica que se rechace un mínimo de reseñas negativo."""
    cliente, _ = cliente_api
    payload = {"sector": "bares", "city": "Bogota", "min_reviews": -1}

    respuesta = cliente.post("/api/v1/busquedas", json=payload)

    assert respuesta.status_code == 422


def test_tc_api_busq_05_datos_incompletos_o_vacios(cliente_api) -> None:
    """Verifica que el sistema rechace búsquedas con texto vacío."""
    cliente, _ = cliente_api
    payload = {"sector": "", "city": "Lima"}

    respuesta = cliente.post("/api/v1/busquedas", json=payload)

    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 2. Pruebas para GET /api/v1/busquedas/{id}
# ---------------------------------------------------------------------------


def test_tc_api_sbusq_01_consultar_busqueda_inexistente(cliente_api) -> None:
    """Verifica que consultar un identificador que no existe devuelva 404."""
    cliente, _ = cliente_api
    id_falso = uuid4()

    respuesta = cliente.get(f"/api/v1/busquedas/{id_falso}")

    assert respuesta.status_code == 404
    assert "búsqueda no encontrada" in respuesta.json()["detail"]


def test_tc_api_sbusq_02_consultar_busqueda_formato_invalido(cliente_api) -> None:
    """Verifica que si se envía un texto que no es UUID devuelva error 422."""
    cliente, _ = cliente_api

    respuesta = cliente.get("/api/v1/busquedas/codigo-invalido-123")

    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 3. Pruebas para GET /api/v1/leads
# ---------------------------------------------------------------------------


def _sembrar_leads_prueba(fabrica, cantidad: int = 5) -> None:
    """Guarda clientes ficticios para probar listas y filtros."""
    with fabrica() as db:
        platform = Platform(name="Google Maps")
        db.add(platform)
        db.flush()

        for i in range(cantidad):
            negocio = Business(
                name=f"Negocio {i}",
                sector="restaurantes" if i % 2 == 0 else "hoteles",
                city="Quito" if i < 3 else "Bogota",
                lead_status="NEW" if i < 4 else "CONTACTED",
            )
            db.add(negocio)
            db.flush()
            db.add(
                BusinessSource(
                    business_id=negocio.business_id,
                    platform_id=platform.platform_id,
                    external_id=f"ext_{i}",
                    rating=Decimal("3.0"),
                    total_reviews=15,
                )
            )
        db.commit()


def test_tc_api_leads_01_listar_leads_con_paginacion(cliente_api) -> None:
    """Verifica que la lista de clientes calcule correctamente las páginas y totales."""
    cliente, fabrica = cliente_api
    _sembrar_leads_prueba(fabrica, cantidad=6)

    # Pedimos la primera página con límite de 2 elementos
    respuesta = cliente.get("/api/v1/leads?page=1&limit=2")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 6
    assert datos["page"] == 1
    assert datos["page_size"] == 2
    assert datos["total_pages"] == 3
    assert datos["has_next"] is True
    assert len(datos["items"]) == 2


def test_tc_api_leads_02_filtro_por_ciudad_y_rubro(cliente_api) -> None:
    """Verifica que se puedan filtrar clientes por ciudad específica."""
    cliente, fabrica = cliente_api
    _sembrar_leads_prueba(fabrica, cantidad=5)

    respuesta = cliente.get("/api/v1/leads?city=Quito")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 3
    assert all(item["city"] == "Quito" for item in datos["items"])


def test_tc_api_leads_03_limite_paginacion_fuera_de_rango(cliente_api) -> None:
    """Verifica que no se permita pedir más de 100 clientes por página."""
    cliente, _ = cliente_api

    # Excedemos el límite superior (101)
    respuesta = cliente.get("/api/v1/leads?limit=101")
    assert respuesta.status_code == 422

    # Límite inferior inválido (0)
    respuesta_cero = cliente.get("/api/v1/leads?limit=0")
    assert respuesta_cero.status_code == 422


# ---------------------------------------------------------------------------
# 4. Pruebas para PATCH /api/v1/leads/{id}/status
# ---------------------------------------------------------------------------


def test_tc_api_patch_01_actualizar_estado_a_contactado(cliente_api) -> None:
    """Verifica que el vendedor pueda marcar un cliente como CONTACTED."""
    cliente, fabrica = cliente_api
    with fabrica() as db:
        negocio = Business(name="Taller Mecanico", lead_status="NEW")
        db.add(negocio)
        db.commit()
        lead_id = negocio.business_id

    respuesta = cliente.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"lead_status": "CONTACTED"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["lead_status"] == "CONTACTED"


def test_tc_api_patch_02_actualizar_estado_acepta_minusculas(cliente_api) -> None:
    """Verifica que el sistema acepte estados escritos en minúsculas y los normalice."""
    cliente, fabrica = cliente_api
    with fabrica() as db:
        negocio = Business(name="Panaderia", lead_status="NEW")
        db.add(negocio)
        db.commit()
        lead_id = negocio.business_id

    respuesta = cliente.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"lead_status": "discarded"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["lead_status"] == "DISCARDED"


def test_tc_api_patch_03_rechazar_estado_no_permitido(cliente_api) -> None:
    """Verifica que se rechacen estados que no existen en el catálogo comercial."""
    _cliente, fabrica = cliente_api
    with fabrica() as db:
        negocio = Business(name="Farmacia", lead_status="NEW")
        db.add(negocio)
        db.commit()

# ---------------------------------------------------------------------------
# 5. Pruebas para Endpoints de Análisis con IA y Cold Email (Issue #73 / #74)
# ---------------------------------------------------------------------------


def test_tc_api_ai_01_consultar_analisis_inexistente(cliente_api) -> None:
    """Verifica que si un cliente no tiene análisis de IA previo, responda 404."""
    cliente, _ = cliente_api
    id_falso = uuid4()

    respuesta = cliente.get(f"/api/v1/leads/{id_falso}/ai-analysis")

    assert respuesta.status_code == 404
    assert "no encontrado" in respuesta.json()["detail"].lower()


def test_tc_api_ai_02_generar_y_consultar_analisis_ia(cliente_api) -> None:
    """Verifica que el endpoint de IA genere el asunto, primer párrafo y clasifique el problema."""
    cliente, fabrica = cliente_api
    from app.models import Review

    with fabrica() as db:
        platform = Platform(name="Google Maps")
        negocio = Business(name="Restaurante Don Pepe", sector="restaurantes", city="Quito")
        db.add_all([platform, negocio])
        db.flush()

        source = BusinessSource(
            business_id=negocio.business_id,
            platform_id=platform.platform_id,
            external_id="rev_test_1",
            rating=Decimal("2.5"),
            total_reviews=10,
        )
        db.add(source)
        db.flush()

        # Agregamos una reseña negativa para que la IA la analice
        db.add(
            Review(
                business_source_id=source.business_source_id,
                external_id="rev_neg_1",
                author="Carlos",
                rating=1,
                content="Muy mala atención del mesero y demoraron 2 horas.",
            )
        )
        db.commit()
        lead_id = negocio.business_id

    # 1. Solicitamos generar el análisis con IA (POST)
    respuesta_post = cliente.post(f"/api/v1/leads/{lead_id}/ai-analysis")
    assert respuesta_post.status_code == 200
    datos = respuesta_post.json()

    # Verificamos que tenga los elementos para el vendedor
    assert datos["category"] in [
        "Atención al cliente",
        "Tiempos de espera",
        "Precios y facturación",
        "Calidad del servicio",
        "Higiene e instalaciones",
        "Otros",
    ]
    assert len(datos["email_subject"]) > 0
    assert len(datos["email_first_paragraph"]) > 0
    assert datos["business_id"] == str(lead_id)

    # 2. Consultamos que haya quedado guardado (GET)
    respuesta_get = cliente.get(f"/api/v1/leads/{lead_id}/ai-analysis")
    assert respuesta_get.status_code == 200
    assert respuesta_get.json()["email_subject"] == datos["email_subject"]


# ---------------------------------------------------------------------------
# 6. Pruebas para Endpoints de Contactos y Scraping Web (Issue #76 / #77)
# ---------------------------------------------------------------------------


def test_tc_api_contact_01_listar_contactos_vacio(cliente_api) -> None:
    """Verifica que un cliente recién creado devuelva una lista de contactos vacía."""
    cliente, fabrica = cliente_api
    with fabrica() as db:
        negocio = Business(name="Hotel Central", city="Bogota")
        db.add(negocio)
        db.commit()
        lead_id = negocio.business_id

    respuesta = cliente.get(f"/api/v1/leads/{lead_id}/contacts")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_tc_api_contact_02_enriquecer_contactos_sin_sitio_web(cliente_api) -> None:
    """Verifica que si el cliente no tiene sitio web, el scraper no reviente y devuelva lista vacía."""
    cliente, fabrica = cliente_api
    with fabrica() as db:
        negocio = Business(name="Kiosco Sin Web", website=None)
        db.add(negocio)
        db.commit()
        lead_id = negocio.business_id

    respuesta = cliente.post(f"/api/v1/leads/{lead_id}/enrich-contacts")

    assert respuesta.status_code == 200
    assert respuesta.json() == []

