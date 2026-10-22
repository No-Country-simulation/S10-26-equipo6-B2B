"""Suite de pruebas unitarias para el extractor de resenas y TDM (Issue #36 y #20).

Trazabilidad: repusense-qa/docs/02_design/test-scenarios.md (TC-EXTR-01 a TC-EXTR-03)
"""

from typing import Any

import pytest

from app.etl.resenas import ErrorRecoleccion, extraer_negativas, limpiar_texto, obtener_pagina


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
