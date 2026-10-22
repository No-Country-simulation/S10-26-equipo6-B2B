"""Pruebas de los contratos de parsing puro del ETL de reseñas.

Son funciones sin red y sin estado. Fijan el formato exacto del payload de
GetLocalBoqProxy, que ``docs/fuente-de-resenas.md`` designa como lo más fácil
de romper al reimplementar el contrato.
"""

import json
from datetime import UTC, datetime

from app.etl.resenas import (
    construir_payload,
    limpiar_texto,
    parsear_cid,
    parsear_epoch_ms,
    resumen_distribucion,
)

# --- parsear_cid -----------------------------------------------------------


def test_parsear_cid_extrae_los_dos_lados():
    cuerpo = "algo 0x91d59a6a396e7a7b:0x7f93a83029608b1a otro"
    assert parsear_cid(cuerpo) == ["0x91d59a6a396e7a7b:0x7f93a83029608b1a"]


def test_parsear_cid_descarta_falso_positivo_por_lado_izquierdo_corto():
    """``0x0:0x...`` no es un CID: el contrato exige 6 hex a cada lado."""
    assert parsear_cid("0x0:0x7f93a83029608b1a") == []


def test_parsear_cid_descarta_falso_positivo_por_lado_derecho_corto():
    assert parsear_cid("0x91d59a6a396e7a7b:0x7f9") == []


def test_parsear_cid_normaliza_el_escape_de_dos_puntos():
    """El JSON escapado trae ``:``; sin normalizar, no haría match."""
    cuerpo = "0x91d59a6a396e7a7b\\u003a0x7f93a83029608b1a"
    assert parsear_cid(cuerpo) == ["0x91d59a6a396e7a7b:0x7f93a83029608b1a"]


def test_parsear_cid_no_repite_el_mismo_cid():
    cuerpo = "0x91d59a6a396e7a7b:0x7f93a83029608b1a y 0x91d59a6a396e7a7b:0x7f93a83029608b1a"
    assert len(parsear_cid(cuerpo)) == 1


def test_parsear_cid_sin_coincidencias_da_lista_vacia():
    assert parsear_cid("una busqueda sin identificadores") == []


# --- construir_payload -----------------------------------------------------


def test_payload_de_primera_pagina_lleva_tamano_y_no_token():
    payload = json.loads(construir_payload("0xabc:0xdef", 2, 20, None))
    sub = payload[1][9]

    assert sub[1] == 2, "la posición 1 del sub-array es el sort"
    assert sub[9] == 20, "la posición 9 es el tamaño de página"
    assert sub[10] is None
    assert sub[11] == ["0xabc:0xdef"]


def test_payload_de_paginacion_mete_el_token_un_nivel_mas_adentro():
    """El token va en la posición 19, no al lado del CID: el error más fácil."""
    payload = json.loads(construir_payload("0xabc:0xdef", 2, 20, "TOKEN"))
    sub = payload[1][9]

    assert sub[9] is None, "en paginación no viaja el tamaño de página"
    assert sub[11] == ["0xabc:0xdef"]
    assert sub[19] == "TOKEN"
    assert "TOKEN" not in sub[:19]


def test_payload_es_json_compacto():
    """El endpoint recibe ``reqpld`` url-encoded: los espacios lo inflan."""
    payload = construir_payload("0xabc:0xdef", 4, 60, None)
    assert " " not in payload
    assert json.loads(payload)[1][9][1] == 4


# --- limpiar_texto ---------------------------------------------------------


def test_limpiar_texto_convierte_br_en_salto_de_linea():
    assert limpiar_texto("una<br>dos") == "una\ndos"


def test_limpiar_texto_acepta_br_autocerrado():
    assert limpiar_texto("una<br/>dos") == "una\ndos"
    assert limpiar_texto("una<BR />dos") == "una\ndos"


def test_limpiar_texto_decodifica_entidades_html():
    assert limpiar_texto("a &amp; b &#39;c&#39;") == "a & b 'c'"


def test_limpiar_texto_sin_str_da_vacio():
    """El payload mete ``None`` en varios índices."""
    assert limpiar_texto(None) == ""


def test_limpiar_texto_quita_espacios_de_orilla():
    assert limpiar_texto("  mala  ") == "mala"


# --- parsear_epoch_ms ------------------------------------------------------


def test_parsear_epoch_ms_convierte_milisegundos_a_utc():
    assert parsear_epoch_ms("1792425050478") == datetime(
        2026, 10, 19, 15, 50, 50, 478000, tzinfo=UTC
    )


def test_parsear_epoch_ms_acepta_entero():
    assert parsear_epoch_ms(1792425050478).year == 2026


def test_parsear_epoch_ms_con_texto_ilegible_da_none():
    assert parsear_epoch_ms("no-es-un-epoch") is None


def test_parsear_epoch_ms_con_none_da_none():
    assert parsear_epoch_ms(None) is None


def test_parsear_epoch_ms_con_bool_da_none():
    """``bool`` es subclase de ``int``: ``True`` no es un epoch."""
    assert parsear_epoch_ms(True) is None


def test_parsear_epoch_ms_con_numero_imposible_da_none():
    assert parsear_epoch_ms("99999999999999999999") is None


# --- resumen_distribucion --------------------------------------------------


def test_resumen_distribucion_cuenta_por_estrella():
    reseñas = [{"estrellas": 1}, {"estrellas": 1}, {"estrellas": 3}, {"estrellas": 5}]
    assert resumen_distribucion(reseñas) == {5: 1, 3: 1, 1: 2}


def test_resumen_distribucion_ignora_las_sin_nota():
    assert resumen_distribucion([{"estrellas": None}, {"estrellas": 2}]) == {2: 1}


def test_resumen_distribucion_ordena_de_mayor_a_menor():
    reseñas = [{"estrellas": 1}, {"estrellas": 5}, {"estrellas": 3}]
    assert list(resumen_distribucion(reseñas)) == [5, 3, 1]


def test_resumen_distribucion_vacio_da_dict_vacio():
    assert resumen_distribucion([]) == {}
