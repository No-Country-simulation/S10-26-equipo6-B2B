"""Suite de pruebas unitarias para el extractor de resenas y TDM (Issue #36 y #20).

Trazabilidad: repusense-qa/docs/02_design/test-scenarios.md (TC-EXTR-01 a TC-EXTR-03)
"""

from datetime import datetime, timezone
from typing import Any

import pytest

from app.etl.resenas import (
    ErrorRecoleccion,
    extraer_negativas,
    limpiar_texto,
    obtener_pagina,
    parsear_epoch_ms,
)


def test_tc_extr_01_aislamiento_y_seleccion_negativas_cotocollao(
    golden_cotocollao: dict[str, Any],
) -> None:
    """TC-EXTR-01: Extrae exactamente las 5 negativas mas recientes con texto del Golden Dataset."""
    resenas_entrada = golden_cotocollao["resenas"]

    seleccionadas = extraer_negativas(resenas_entrada, cantidad=5)

    assert len(seleccionadas) == 5
    ids_obtenidos = [r["id"] for r in seleccionadas]
    assert ids_obtenidos == [
        "rev_cot_01",
        "rev_cot_04",
        "rev_cot_05",
        "rev_cot_06",
        "rev_cot_07",
    ]
    assert all(r["texto"].strip() != "" for r in seleccionadas)
    assert all(r["estrellas"] <= 3 for r in seleccionadas)


def test_tc_extr_02_sanitizacion_entidades_html_y_saltos_de_linea() -> None:
    """TC-EXTR-02: limpiar_texto convierte <br> en salto de linea y decodifica entidades HTML."""
    sucio = "Mala higiene &amp; suciedad<br>no lo recomiendo."

    limpio = limpiar_texto(sucio)

    assert limpio == "Mala higiene & suciedad\nno lo recomiendo."


def test_tc_extr_03_resiliencia_estructura_mutada_boqproxy(
    monkeypatch: pytest.MonkeyPatch,
    golden_payload_corrupto_boqproxy: str,
) -> None:
    """TC-EXTR-03: Payload con prefijo )]}' pero sin data[1][10] lanza ErrorRecoleccion."""
    assert golden_payload_corrupto_boqproxy.startswith(")]}'")
    monkeypatch.setattr(
        "app.etl.resenas.http_get",
        lambda url, timeout=30: (golden_payload_corrupto_boqproxy, 200),
    )

    with pytest.raises(ErrorRecoleccion, match="cambio de estructura"):
        obtener_pagina("0x91d59a6a396e7a7b:0x7f93a83029608b1a", orden=2, tamano_pagina=20)


def test_tc_extr_04_bva_frontera_filtro_max_estrellas_configurable() -> None:
    """TC-EXTR-04: Analisis de frontera para max_estrellas (<= 3 vs <= 2)."""
    resenas = [
        {"id": "r1", "estrellas": 1, "texto": "Pesimo"},
        {"id": "r2", "estrellas": 2, "texto": "Malo"},
        {"id": "r3", "estrellas": 3, "texto": "Regular"},
        {"id": "r4", "estrellas": 4, "texto": "Bueno"},
        {"id": "r5", "estrellas": 5, "texto": "Excelente"},
    ]

    # Con el nuevo umbral configurable por defecto (max_estrellas=3)
    negativas_3 = extraer_negativas(resenas, cantidad=10, max_estrellas=3)
    ids_3 = [r["id"] for r in negativas_3]
    assert ids_3 == ["r1", "r2", "r3"]
    assert all(r["estrellas"] <= 3 for r in negativas_3)

    # Con umbral restrictivo previo (max_estrellas=2)
    negativas_2 = extraer_negativas(resenas, cantidad=10, max_estrellas=2)
    ids_2 = [r["id"] for r in negativas_2]
    assert ids_2 == ["r1", "r2"]
    assert "r3" not in ids_2


def test_tc_extr_05_resiliencia_epoch_ms_a_utc() -> None:
    """TC-EXTR-05: parsear_epoch_ms retorna datetime UTC o None defensivo ante mutaciones."""
    # Caso valido: epoch conocido
    # 1700000000000 ms = 2023-11-14 22:13:20 UTC
    dt = parsear_epoch_ms("1700000000000")
    assert isinstance(dt, datetime)
    assert dt == datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)

    # Casos defensivos de Google / payload sucio
    assert parsear_epoch_ms(None) is None
    assert parsear_epoch_ms("no_es_un_numero") is None
    assert parsear_epoch_ms(True) is None
    assert parsear_epoch_ms(False) is None


def test_tc_extr_06_estampado_scraped_at_por_lote(monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-EXTR-06: obtener_resenas asigna scraped_at UTC consistente a todo el lote."""
    from app.etl import resenas as mod_resenas

    # Mock de cids
    monkeypatch.setattr(mod_resenas, "obtener_cids", lambda consulta: ["cid_dummy_01"])

    # Mock de pagina con 2 resenas en formato crudo
    raw_resenas = [
        [None, 1, ["Hace una semana", None, "1700000000000"], ["Juan"], None, "id_01", None, None, None, None, None, "Malo"],
        [None, 2, ["Hace 2 dias", None, "1700100000000"], ["Pedro"], None, "id_02", None, None, None, None, None, "Regular"],
    ]
    monkeypatch.setattr(mod_resenas, "obtener_pagina", lambda cid, orden, tamano, token: (raw_resenas, None))

    lote, cid_usado = mod_resenas.obtener_resenas("clinica quito")

    assert cid_usado == "cid_dummy_01"
    assert len(lote) == 2
    # Ambos deben tener scraped_at en datetime UTC idéntico
    assert isinstance(lote[0]["scraped_at"], datetime)
    assert isinstance(lote[1]["scraped_at"], datetime)
    assert lote[0]["scraped_at"] == lote[1]["scraped_at"]
    assert lote[0]["fecha_absoluta"] == datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)

