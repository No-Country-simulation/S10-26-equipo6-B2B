"""Clientes de fuentes externas (SerpApi y Google Maps)."""

from app.infrastructure.external.google_maps_client import (
    ErrorRecoleccion,
    GoogleMapsClient,
)
from app.infrastructure.external.serpapi_client import (
    DiscoveryError,
    SerpApiClient,
    SerpApiDiscovery,
)

__all__ = [
    "DiscoveryError",
    "ErrorRecoleccion",
    "GoogleMapsClient",
    "SerpApiClient",
    "SerpApiDiscovery",
]
