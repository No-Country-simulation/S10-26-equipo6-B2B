"""Tests del discovery: normalizacion, filtros del brief y fail-fast.

El transporte HTTP se inyecta como dependencia: no hay red en los tests
(el borde del sistema es lo unico que se simula).
"""

import json

import pytest

from app.core.config import settings
from app.providers.discovery import DiscoveryError, SerpApiDiscovery


def _respuesta_serpapi(resultados: list[dict], next_url: str | None = None) -> str:
    cuerpo: dict = {"local_results": resultados}
    if next_url:
        cuerpo["serpapi_pagination"] = {"next": next_url}
    return json.dumps(cuerpo)


def _transporte_simple(cuerpo: str):
    """Transporte falso que siempre devuelve el mismo cuerpo y registra URLs."""
    llamadas: list[str] = []

    def transporte(url: str) -> tuple[str, int]:
        llamadas.append(url)
        return cuerpo, 200

    return transporte, llamadas


def _negocio_serpapi(**extra) -> dict:
    base = {
        "position": 1,
        "title": "Taller 24 horas",
        "place_id": "ChIJabc123",
        "rating": 3.2,
        "reviews": 29,
        "type": "Taller mecanico",
        "address": "Calle 123, Bogota",
        "phone": "+57 601 123 4567",
        "website": "https://taller24.co",
    }
    base.update(extra)
    return base


@pytest.fixture(autouse=True)
def _filtros_del_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fija los filtros del brief para que el test no dependa del .env local."""
    monkeypatch.setattr(settings, "discovery_max_rating", 3.5)
    monkeypatch.setattr(settings, "discovery_min_reviews", 10)


def test_normaliza_los_campos_del_negocio() -> None:
    transporte, _ = _transporte_simple(_respuesta_serpapi([_negocio_serpapi()]))
    discovery = SerpApiDiscovery(transporte, api_key="k-test", espera_s=0)

    negocios = discovery.buscar_negocios("taller mecanico", "Bogota")

    assert len(negocios) == 1
    negocio = negocios[0]
    assert negocio.nombre == "Taller 24 horas"
    assert negocio.rating == 3.2
    assert negocio.total_resenas == 29
    assert negocio.telefono == "+57 601 123 4567"
    assert negocio.website == "https://taller24.co"
    assert negocio.direccion == "Calle 123, Bogota"
    assert negocio.place_id == "ChIJabc123"
    assert negocio.rubro == "Taller mecanico"


def test_aplica_los_filtros_del_brief() -> None:
    resultados = [
        _negocio_serpapi(rating=3.2, reviews=29), # pasa
        _negocio_serpapi(rating=4.9, reviews=691), # rating alto: fuera
        _negocio_serpapi(rating=3.2, reviews=5), # pocas resenas: fuera
        _negocio_serpapi(rating=3.5, reviews=30), # frontera rating: fuera (< 3.5 estricto)
        _negocio_serpapi(rating=3.4, reviews=10), # frontera resenas: fuera (> 10 estricto)
    ]
    transporte, _ = _transporte_simple(_respuesta_serpapi(resultados))
    discovery = SerpApiDiscovery(transporte, api_key="k-test", espera_s=0)

    negocios = discovery.buscar_negocios("taller mecanico", "Bogota")

    assert [negocio.rating for negocio in negocios] == [3.2]


def test_descarta_resultados_sin_metricas_o_sin_place_id() -> None:
    resultados = [
        _negocio_serpapi(rating=None, reviews=None), # sin metricas: no evaluable
        {"title": "Sin place", "rating": 3.0, "reviews": 50}, # sin place_id: no persistible
    ]
    transporte, _ = _transporte_simple(_respuesta_serpapi(resultados))
    discovery = SerpApiDiscovery(transporte, api_key="k-test", espera_s=0)

    negocios = discovery.buscar_negocios("taller mecanico", "Bogota")

    assert negocios == []


def test_falla_rapido_sin_api_key() -> None:
    transporte, llamadas = _transporte_simple(_respuesta_serpapi([]))
    discovery = SerpApiDiscovery(transporte, api_key="", espera_s=0)

    with pytest.raises(DiscoveryError, match="SERPAPI_KEY"):
        discovery.buscar_negocios("taller mecanico", "Bogota")

    assert llamadas == [] # no gasto ninguna busqueda


def _transporte_paginado(paginas: list[str]):
    """Transporte falso que sirve las paginas en orden y registra las URLs."""
    llamadas: list[str] = []

    def transporte(url: str) -> tuple[str, int]:
        llamadas.append(url)
        return paginas[len(llamadas) - 1], 200

    return transporte, llamadas


def test_pagina_hasta_que_no_hay_siguiente() -> None:
    pagina1 = _respuesta_serpapi(
        [_negocio_serpapi(place_id="ChIJp1", rating=3.0, reviews=20)],
        next_url="https://serpapi.com/search?start=20",
    )
    pagina2 = _respuesta_serpapi(
        [_negocio_serpapi(place_id="ChIJp2", rating=2.8, reviews=40)],
    )
    transporte, llamadas = _transporte_paginado([pagina1, pagina2])
    discovery = SerpApiDiscovery(transporte, api_key="k-test", espera_s=0)

    negocios = discovery.buscar_negocios("taller mecanico", "Bogota")

    assert [negocio.place_id for negocio in negocios] == ["ChIJp1", "ChIJp2"]
    assert len(llamadas) == 2
    assert "start=20" in llamadas[1]


def test_respeta_el_maximo_de_paginas() -> None:
    siguiente = "https://serpapi.com/search?start=20"
    paginas = [_respuesta_serpapi([_negocio_serpapi()], next_url=siguiente)] * 99
    transporte, llamadas = _transporte_paginado(paginas)
    discovery = SerpApiDiscovery(
        transporte, api_key="k-test", espera_s=0, max_paginas=3
    )

    discovery.buscar_negocios("taller mecanico", "Bogota")

    assert len(llamadas) == 3


def test_error_http_lanza_discovery_error() -> None:
    def transporte(url: str) -> tuple[str, int]:
        return '{"error": "Invalid API key"}', 401

    discovery = SerpApiDiscovery(transporte, api_key="mala", espera_s=0)

    with pytest.raises(DiscoveryError, match="401"):
        discovery.buscar_negocios("taller mecanico", "Bogota")


def test_error_reportado_por_serpapi_lanza_discovery_error() -> None:
    transporte, _ = _transporte_simple(
        json.dumps({"error": "Your account is suspended"})
    )
    discovery = SerpApiDiscovery(transporte, api_key="k-test", espera_s=0)

    with pytest.raises(DiscoveryError, match="suspended"):
        discovery.buscar_negocios("taller mecanico", "Bogota")
