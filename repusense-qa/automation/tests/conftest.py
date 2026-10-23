"""Fixtures modulares de Pytest para TDM y aislamiento de red (Issue #20 / #40 / #36)."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.config import settings

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "data" / "golden_datasets"


@pytest.fixture(autouse=True)
def _fijar_filtros_del_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garantiza que los umbrales del brief (< 3.5 estrellas, > 10 resenas) sean deterministas."""
    monkeypatch.setattr(settings, "discovery_max_rating", 3.5)
    monkeypatch.setattr(settings, "discovery_min_reviews", 10)


@pytest.fixture
def golden_serpapi_bva_raw() -> str:
    """Devuelve el JSON crudo del Golden Dataset BVA de SerpApi."""
    return (GOLDEN_DIR / "serpapi_discovery_bva.json").read_text(encoding="utf-8")


@pytest.fixture
def golden_cotocollao() -> dict[str, Any]:
    """Devuelve el Golden Dataset critico de Clinica Cotocollao."""
    raw = (GOLDEN_DIR / "dataset_critico_cotocollao.json").read_text(encoding="utf-8")
    return json.loads(raw)


@pytest.fixture
def golden_payload_corrupto_boqproxy() -> str:
    """Devuelve el payload corrupto con prefijo anti-XSSI )]}' pero sin estructura esperada."""
    return (GOLDEN_DIR / "payload_corrupto_boqproxy.json").read_text(encoding="utf-8")
