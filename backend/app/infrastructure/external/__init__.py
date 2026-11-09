"""Clientes de fuentes externas (SerpApi y Google Maps)."""

from app.infrastructure.external.google_maps_client import (
    ErrorRecoleccion,
    GoogleMapsClient,
)
from app.infrastructure.external.llm_client import LLMClient
from app.infrastructure.external.serpapi_client import (
    DiscoveryError,
    SerpApiClient,
    SerpApiDiscovery,
)
from app.infrastructure.external.website_scraper import WebsiteScraper

__all__ = [
    "DiscoveryError",
    "ErrorRecoleccion",
    "GoogleMapsClient",
    "LLMClient",
    "SerpApiClient",
    "SerpApiDiscovery",
    "WebsiteScraper",
]
