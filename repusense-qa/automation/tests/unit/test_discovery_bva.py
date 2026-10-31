"""Suite de pruebas unitarias y BVA para el modulo de Discovery (Issue #40).

Trazabilidad: repusense-qa/docs/02_design/test-scenarios.md (TC-DISC-01 a TC-DISC-05)
"""

import json

import pytest

from app.providers.discovery import DiscoveryError, SerpApiDiscovery


def _mock_serpapi(resultados: list[dict], next_url: str | None = None) -> str:
    payload: dict = {"local_results": resultados}
    if next_url:
        payload["serpapi_pagination"] = {"next": next_url}
    return json.dumps(payload)


def test_tc_disc_01_frontera_valida_rating_3_4_y_reviews_11() -> None:
    """TC-DISC-01: Lead en frontera superior valida (rating=3.4, reviews=11) es ACEPTADO."""
    cuerpo = _mock_serpapi([
        {
            "title": "Clínica Dental X",
            "place_id": "ChIJ_disc_01",
            "rating": 3.4,
            "reviews": 11,
            "phone": "+57 601 555 0101",
            "website": "https://clinicadentalx.co",
            "address": "Av. Caracas 45-10, Bogotá",
            "type": "Clínica dental",
            "business_status": "OPERATIONAL",
        }
    ])
    discovery = SerpApiDiscovery(lambda url: (cuerpo, 200), api_key="k-qa", espera_s=0)

    negocios = discovery.buscar_negocios("clínica dental", "Bogotá")

    assert len(negocios) == 1
    lead = negocios[0]
    assert lead.nombre == "Clínica Dental X"
    assert lead.rating == 3.4
    assert lead.total_resenas == 11
    assert lead.place_id == "ChIJ_disc_01"
    assert lead.estado_operativo == "OPERATIONAL"


def test_tc_disc_02_descarte_limite_superior_rechazado_rating_3_5() -> None:
    """TC-DISC-02: Negocio en limite exacto rechazado (rating=3.5, reviews=20) es DESCARTADO."""
    cuerpo = _mock_serpapi([
        {
            "title": "Restaurante Y",
            "place_id": "ChIJ_disc_02",
            "rating": 3.5,
            "reviews": 20,
        }
    ])
    discovery = SerpApiDiscovery(lambda url: (cuerpo, 200), api_key="k-qa", espera_s=0)

    assert discovery.buscar_negocios("restaurante", "Bogotá") == []


def test_tc_disc_03_descarte_limite_frontera_rechazado_reviews_10() -> None:
    """TC-DISC-03: Negocio en limite exacto rechazado (rating=2.8, reviews=10) es DESCARTADO."""
    cuerpo = _mock_serpapi([
        {
            "title": "Taller Z",
            "place_id": "ChIJ_disc_03",
            "rating": 2.8,
            "reviews": 10,
        }
    ])
    discovery = SerpApiDiscovery(lambda url: (cuerpo, 200), api_key="k-qa", espera_s=0)

    assert discovery.buscar_negocios("taller mecánico", "Bogotá") == []


def test_tc_disc_bva_lote_completo_golden_dataset(golden_serpapi_bva_raw: str) -> None:
    """Valida el lote mixto del Golden Dataset (serpapi_discovery_bva.json) en una sola pasada."""
    discovery = SerpApiDiscovery(
        lambda url: (golden_serpapi_bva_raw, 200), api_key="k-qa", espera_s=0
    )

    negocios = discovery.buscar_negocios("clínica dental", "Bogotá")

    assert [n.place_id for n in negocios] == ["ChIJ_bva_valid_34_11"]


def test_tc_disc_04_paginacion_mandatoria_ante_resultados_criticos_diluidos() -> None:
    """TC-DISC-04: No aborta cuando pagina 1 trae 0 leads; avanza via serpapi_pagination.next."""
    pag1 = _mock_serpapi(
        [{"title": "Dental Top", "place_id": "ChIJ_top", "rating": 4.8, "reviews": 120}],
        next_url="https://serpapi.com/search?start=20",
    )
    pag2 = _mock_serpapi(
        [{"title": "Dental Crisis", "place_id": "ChIJ_crisis", "rating": 2.9, "reviews": 45}]
    )
    paginas = [pag1, pag2]
    urls_llamadas: list[str] = []

    def transporte(url: str) -> tuple[str, int]:
        urls_llamadas.append(url)
        return paginas[len(urls_llamadas) - 1], 200

    discovery = SerpApiDiscovery(transporte, api_key="k-qa", espera_s=0)

    negocios = discovery.buscar_negocios("clínica dental", "Bogotá")

    assert len(urls_llamadas) == 2
    assert "start=" not in urls_llamadas[0]
    assert "start=20" in urls_llamadas[1]
    assert [n.place_id for n in negocios] == ["ChIJ_crisis"]


def test_tc_disc_rate_limiting_intervalo_entre_paginas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica que espera_s se ejecute entre paginas subsiguientes y no antes de la primera."""
    pausas: list[float] = []
    monkeypatch.setattr("app.providers.discovery.time.sleep", lambda s: pausas.append(s))

    pag = _mock_serpapi(
        [{"title": "Lead", "place_id": "ChIJ_1", "rating": 3.0, "reviews": 20}],
        next_url="https://serpapi.com/search?start=20",
    )
    discovery = SerpApiDiscovery(
        lambda url: (pag, 200), api_key="k-qa", espera_s=2.0, max_paginas=3
    )

    discovery.buscar_negocios("taller", "Bogotá")

    assert pausas == [2.0, 2.0]


def test_tc_disc_05_captura_http_429_con_codigo_accionable() -> None:
    """TC-DISC-05 (Parte 1): Captura HTTP 429 en DiscoveryError sin crash no controlado."""
    discovery = SerpApiDiscovery(
        lambda url: ('{"error": "Rate limit exceeded (50/hour)"}', 429),
        api_key="k-qa",
        espera_s=0,
    )

    with pytest.raises(DiscoveryError) as exc_info:
        discovery.buscar_negocios("taller", "Bogotá")

    assert exc_info.value.codigo == 429


@pytest.mark.xfail(
    reason="Hallazgo QA Issue #40: SerpApiDiscovery aun no implementa reintento con backoff exponencial ante HTTP 429",
    strict=True,
)
def test_tc_disc_05_backoff_exponencial_ante_http_429() -> None:
    """TC-DISC-05 (Parte 2): Verifica reintento con backoff exponencial ante HTTP 429."""
    intentos = 0

    def transporte_429(url: str) -> tuple[str, int]:
        nonlocal intentos
        intentos += 1
        return '{"error": "Rate limit exceeded"}', 429

    discovery = SerpApiDiscovery(transporte_429, api_key="k-qa", espera_s=0)

    with pytest.raises(DiscoveryError):
        discovery.buscar_negocios("taller", "Bogotá")

    assert intentos > 1


@pytest.mark.xfail(
    reason="Hallazgo QA Issue #40: buscar_negocios() no deduplica por place_id cuando un negocio se repite entre paginas",
    strict=True,
)
def test_tc_disc_deduplicacion_place_id_entre_paginas() -> None:
    """Verifica que un mismo place_id repetido entre pagina 1 y pagina 2 no se duplique en memoria."""
    negocio_repetido = {
        "title": "Taller Repetido",
        "place_id": "ChIJ_dup_01",
        "rating": 3.1,
        "reviews": 25,
    }
    paginas = [
        _mock_serpapi([negocio_repetido], next_url="https://serpapi.com/search?start=20"),
        _mock_serpapi([negocio_repetido]),
    ]
    idx = 0

    def transporte(url: str) -> tuple[str, int]:
        nonlocal idx
        resp = paginas[idx]
        idx += 1
        return resp, 200

    discovery = SerpApiDiscovery(transporte, api_key="k-qa", espera_s=0)
    negocios = discovery.buscar_negocios("taller", "Bogotá")

    assert len(negocios) == 1
