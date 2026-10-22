"""Pruebas del contrato de reseñas que expone la capa ETL.

El esquema no se define a ojo: cada prueba alimenta ``Resena`` con la salida
real de ``extraer_campos``, así el contrato queda amarrado a lo que el
endpoint de Google devuelve de verdad.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.etl.resenas import extraer_campos
from app.schemas.resenas import Resena


def _cruda(
    estrellas=1, texto="mala", autor="ana", fecha="Hace 2 semanas", id_="id-1", epoch_ms=None
):
    """Reseña cruda con la forma posicional que devuelve GetLocalBoqProxy.

    El texto vive en el índice 27; los demás campos, en 1, 2, 3 y 5. La
    posición 2 es una lista cuyo primer elemento es el texto relativo y cuyo
    tercer elemento es el epoch en milisegundos, serializado como string.
    """
    cruda = [None] * 28
    cruda[1] = estrellas
    cruda[2] = [fecha, None, epoch_ms] if epoch_ms is not None else [fecha]
    cruda[3] = [autor]
    cruda[5] = id_
    cruda[27] = texto
    return cruda


def test_valida_la_salida_real_del_etl():
    resena = Resena(**extraer_campos(_cruda()))
    assert resena.estrellas == 1
    assert resena.autor == "ana"
    assert resena.fecha == "Hace 2 semanas"
    assert resena.id == "id-1"
    assert resena.texto == "mala"


def test_fecha_relativa_se_conserva_junto_a_la_absoluta():
    """La fuente entrega el texto relativo además del epoch; ninguno desplaza al otro."""
    resena = Resena(**extraer_campos(_cruda(fecha="Hace 2 meses")))
    assert resena.fecha == "Hace 2 meses"


def test_extrae_fecha_absoluta_desde_el_payload():
    """El epoch en milisegundos de la posición 2 da la fecha exacta en UTC."""
    resena = Resena(**extraer_campos(_cruda(fecha="Hace 3 días", epoch_ms="1792425050478")))

    assert resena.fecha_absoluta == datetime(2026, 10, 19, 15, 50, 50, 478000, tzinfo=UTC)
    assert resena.fecha_absoluta.tzinfo is UTC
    assert resena.fecha == "Hace 3 días"


def test_fecha_absoluta_es_none_cuando_el_payload_no_la_trae():
    """Algunas reseñas solo traen el texto relativo; no deben romper el contrato."""
    resena = Resena(**extraer_campos(_cruda(fecha="Hace 2 meses")))

    assert resena.fecha_absoluta is None
    assert resena.fecha == "Hace 2 meses"


def test_epoch_malformado_degrada_a_none():
    """Google puede cambiar el formato sin aviso: debe degradar, no lanzar."""
    resena = Resena(**extraer_campos(_cruda(fecha="Hace 1 mes", epoch_ms="no-es-un-epoch")))

    assert resena.fecha_absoluta is None
    assert resena.fecha == "Hace 1 mes"


def test_scraped_at_acepta_datetime():
    """ERD ``systemDesign.md:270``: ``review.scraped_at`` es timestamp, no texto."""
    resena = Resena(**extraer_campos(_cruda()), scraped_at=datetime(2026, 10, 22, tzinfo=UTC))

    assert resena.scraped_at == datetime(2026, 10, 22, tzinfo=UTC)


def test_scraped_at_es_none_hasta_que_lo_selle_el_lote():
    """``extraer_campos`` no lo llena porque no viene del payload: lo estampa el lote."""
    resena = Resena(**extraer_campos(_cruda()))

    assert resena.scraped_at is None


def test_acepta_resena_sin_texto():
    """Google devuelve reseñas sin cuerpo; no deben romper el contrato."""
    resena = Resena(**extraer_campos(_cruda(texto="")))
    assert resena.texto == ""
    assert resena.estrellas == 1


def test_estrellas_puede_ser_none():
    """El endpoint a veces omite la calificación."""
    resena = Resena(**extraer_campos(_cruda(estrellas=None)))
    assert resena.estrellas is None


def test_id_vacio_por_defecto():
    """El ETL devuelve '' cuando la posición 5 no existe."""
    resena = Resena(**extraer_campos(_cruda(id_="")))
    assert resena.id == ""


def test_rechaza_estrellas_fuera_de_rango():
    """Una calificación fuera de 1..5 es dato corrupto, no una reseña."""
    with pytest.raises(ValidationError):
        Resena(**extraer_campos(_cruda(estrellas=9)))
