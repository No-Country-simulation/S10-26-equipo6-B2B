"""Pruebas del contrato de reseñas que expone la capa ETL.

El esquema no se define a ojo: cada prueba alimenta ``Resena`` con la salida
real de ``extraer_campos``, así el contrato queda amarrado a lo que el
endpoint de Google devuelve de verdad.
"""

import pytest
from pydantic import ValidationError

from app.etl.resenas import extraer_campos
from app.schemas.resenas import Resena


def _cruda(estrellas=1, texto="mala", autor="ana", fecha="Hace 2 semanas", id_="id-1"):
    """Reseña cruda con la forma posicional que devuelve GetLocalBoqProxy.

    El texto vive en el índice 27; los demás campos, en 1, 2, 3 y 5.
    """
    cruda = [None] * 28
    cruda[1] = estrellas
    cruda[2] = [fecha]
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


def test_fecha_es_texto_relativo_y_no_timestamp():
    """La fuente entrega 'Hace 2 meses', no una fecha parseable."""
    resena = Resena(**extraer_campos(_cruda(fecha="Hace 2 meses")))
    assert resena.fecha == "Hace 2 meses"


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
