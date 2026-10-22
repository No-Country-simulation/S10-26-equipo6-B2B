"""Pruebas de contrato sobre los esquemas Pydantic de Discovery (#40) y Resenas (#36)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.discovery import Negocio
from app.schemas.resenas import Resena


def test_contrato_configuracion_base_issue_28() -> None:
    """Valida los valores por defecto del contrato Settings (Issue #28 / #40 / #36)."""
    cfg = Settings(_env_file=None)
    assert cfg.app_name == "RepuSense API"
    assert cfg.version == "0.1.0"
    assert cfg.discovery_max_rating == 3.5
    assert cfg.discovery_min_reviews == 10
    assert cfg.etl_negative_rating_max == 3


def test_contrato_negocio_campos_minimos_y_opcionales() -> None:
    """Valida que Negocio acepte campos obligatorios y asigne None a los opcionales."""
    negocio = Negocio(
        nombre="Taller 24 horas",
        rating=3.2,
        total_resenas=29,
        place_id="ChIJabc123",
    )

    assert negocio.telefono is None
    assert negocio.website is None
    assert negocio.direccion is None
    assert negocio.rubro is None
    assert negocio.estado_operativo is None


def test_contrato_negocio_rechaza_sin_place_id() -> None:
    """place_id es la clave de identidad obligatoria del contrato."""
    with pytest.raises(ValidationError):
        Negocio(nombre="Sin ID", rating=3.0, total_resenas=15)  # type: ignore[call-arg]


def test_contrato_resena_valida_rango_estrellas_1_a_5() -> None:
    """El contrato de Resena restringe estrellas al intervalo [1, 5]."""
    resena = Resena(id="r1", estrellas=1, fecha="hace un mes", autor="Ana", texto="Mal servicio")
    assert resena.estrellas == 1

    with pytest.raises(ValidationError):
        Resena(id="r2", estrellas=6, fecha="hoy", autor="Ana", texto="Invalido")
