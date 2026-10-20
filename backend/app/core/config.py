"""Configuracion de la API, cargada desde .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RepuSense API"
    version: str = "0.1.0"

    # Infraestructura local via Docker. No hay servicios externos de pago.
    database_url: str = "postgresql+psycopg://repusense:repusense@localhost:5432/repusense"
    redis_url: str = "redis://localhost:6379/0"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Una "resena negativa" es rating <= 3. Decision del equipo,
    # consistente con el < 3.5 del brief porque review.rating es smallint 1-5.
    etl_negative_rating_max: int = 3
    etl_max_reviews_per_business: int = 50

    # Discovery via SerpApi Google Maps. Contrato y limites en
    # docs/fuente-de-discovery.md (free tier: 250 busquedas/mes, 50/hora).
    serpapi_key: str = ""
    discovery_max_rating: float = 3.5  # brief: < 3.5 estrellas
    discovery_min_reviews: int = 10  # brief: > 10 resenas
    discovery_max_paginas: int = 6  # Maps corta a ~120 resultados por query
    discovery_request_interval: float = 2.0  # cortesia entre paginas (segundos)
    discovery_gl: str = "mx"


settings = Settings()
