"""Pruebas de la capa de extracción de reseñas negativas.

Fija el umbral documentado en ``docs/fuente-de-resenas.md`` y en RF2 del
``docs/systemDesign.md``: una reseña es negativa cuando su ``rating <= 3`` y
su ``content`` no está vacío. Usa reseñas fabricadas, sin red.
"""

from datetime import UTC

from app.etl import resenas
from app.etl.resenas import extraer_negativas


def _resena(estrellas, texto, id_="r-1"):
    """Reseña fabricada con la forma exacta que devuelve ``extraer_campos``."""
    return {
        "estrellas": estrellas,
        "fecha": "2026-01-01",
        "autor": "ana",
        "id": id_,
        "texto": texto,
    }


def test_una_estrella_entra():
    reseñas = [_resena(1, "mala")]
    assert [r["texto"] for r in extraer_negativas(reseñas, 5)] == ["mala"]


def test_dos_estrellas_entra():
    reseñas = [_resena(2, "regular")]
    assert [r["texto"] for r in extraer_negativas(reseñas, 5)] == ["regular"]


def test_tres_estrellas_entra():
    """RF2: el umbral es ``<= 3``, no ``<= 2``."""
    reseñas = [_resena(3, "aceptable")]
    assert [r["texto"] for r in extraer_negativas(reseñas, 5)] == ["aceptable"]


def test_cuatro_estrellas_no_entra():
    reseñas = [_resena(4, "buena")]
    assert extraer_negativas(reseñas, 5) == []


def test_cinco_estrellas_no_entra():
    reseñas = [_resena(5, "excelente")]
    assert extraer_negativas(reseñas, 5) == []


def test_estrellas_none_no_entra():
    reseñas = [_resena(None, "sin nota")]
    assert extraer_negativas(reseñas, 5) == []


def test_sin_texto_no_ocupa_plaza():
    """Una reseña vacía no consume una de las N plazas."""
    reseñas = [_resena(1, "", "vacia"), _resena(2, "con texto", "llena")]
    salida = extraer_negativas(reseñas, 1)
    assert [r["texto"] for r in salida] == ["con texto"]


def test_respeta_la_cantidad():
    reseñas = [
        _resena(1, "primera", "r1"),
        _resena(2, "segunda", "r2"),
        _resena(3, "tercera", "r3"),
    ]
    assert [r["texto"] for r in extraer_negativas(reseñas, 2)] == ["primera", "segunda"]


def test_orden_de_recepcion_se_conserva():
    """Devuelve las más recientes primero: el orden del endpoint manda."""
    reseñas = [
        _resena(1, "reciente", "r1"),
        _resena(3, "mediana", "r2"),
        _resena(2, "antigua", "r3"),
    ]
    assert [r["texto"] for r in extraer_negativas(reseñas, 3)] == [
        "reciente",
        "mediana",
        "antigua",
    ]


def test_obtener_negativas_expone_el_umbral(monkeypatch):
    """La función pública filtra sin tocar la red."""
    fabricadas = [
        _resena(1, "mala", "a"),
        _resena(3, "regular", "b"),
        _resena(5, "buena", "c"),
    ]

    def _falso(consulta, orden=2, tamano_pagina=20, max_paginas=6, max_resenas=100):
        return fabricadas, "0x000001:0x000002"

    monkeypatch.setattr(resenas, "obtener_resenas", _falso)
    salida = resenas.obtener_negativas("negocio fabricado", cantidad=5)
    assert [r["texto"] for r in salida] == ["mala", "regular"]


def test_obtener_negativas_respeta_cantidad(monkeypatch):
    fabricadas = [
        _resena(1, "primera", "a"),
        _resena(2, "segunda", "b"),
        _resena(3, "tercera", "c"),
    ]

    def _falso(consulta, orden=2, tamano_pagina=20, max_paginas=6, max_resenas=100):
        return fabricadas, "0x000001:0x000002"

    monkeypatch.setattr(resenas, "obtener_resenas", _falso)
    assert len(resenas.obtener_negativas("negocio fabricado", cantidad=2)) == 2


def test_max_estrellas_es_inyectable():
    """El umbral no está hardcodeado: se cambia por parámetro, sin tocar el entorno."""
    reseñas = [_resena(4, "buena"), _resena(3, "aceptable")]
    salida = extraer_negativas(reseñas, 5, max_estrellas=4)
    assert [r["texto"] for r in salida] == ["buena", "aceptable"]


def test_max_estrellas_por_defecto_sigue_siendo_tres():
    """RF2: sin umbral explícito el corte sigue en ``<= 3``."""
    assert [r["texto"] for r in extraer_negativas([_resena(4, "buena")], 5)] == []


def test_obtener_negativas_lee_el_umbral_de_settings(monkeypatch):
    """``settings.etl_negative_rating_max`` es el que manda, no un literal."""
    fabricadas = [_resena(4, "buena", "a")]

    def _falso(consulta, orden=2, tamano_pagina=20, max_paginas=6, max_resenas=100):
        return fabricadas, "0x000001:0x000002"

    monkeypatch.setattr(resenas, "obtener_resenas", _falso)
    monkeypatch.setattr("app.core.config.settings.etl_negative_rating_max", 4)

    assert [r["texto"] for r in resenas.obtener_negativas("negocio fabricado")] == ["buena"]


def test_obtener_resenas_sella_scraped_at_una_vez_por_lote(monkeypatch):
    """ERD ``systemDesign.md:270``: ``review.scraped_at`` cronometra la recolección."""
    cruda = [None] * 28
    cruda[1] = 1
    cruda[2] = ["Hace 1 mes", None, "1789481075334"]
    cruda[3] = ["ana"]
    cruda[5] = "id-1"
    cruda[27] = "mala"

    monkeypatch.setattr(resenas, "obtener_cids", lambda q: ["0x000001:0x000002"])
    monkeypatch.setattr(
        resenas, "obtener_pagina", lambda cid, orden, tamano, token=None: ([cruda], None)
    )

    salida, cid = resenas.obtener_resenas("negocio fabricado")

    assert cid == "0x000001:0x000002"
    assert salida[0]["scraped_at"] is not None
    assert salida[0]["scraped_at"].tzinfo is UTC
