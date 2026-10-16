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


settings = Settings()
