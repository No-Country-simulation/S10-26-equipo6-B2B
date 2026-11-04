"""Configuración de SQLAlchemy: engine, sesiones y ciclo de vida del esquema."""

from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models import Base, Platform, ProblemCategory

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

PROBLEM_CATEGORIES = (
    "Atención al cliente",
    "Precios",
    "Higiene",
    "Demoras",
)


def get_db() -> Generator[Session, None, None]:
    """Generador de sesión: la cierra al terminar la petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea el esquema (MVP) y siembra los catálogos maestros."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_catalogs(db)


def seed_catalogs(db: Session) -> None:
    """Garantiza la plataforma de Google Maps y las categorías del LLM."""
    if db.scalar(select(Platform).where(Platform.name == "Google Maps")) is None:
        db.add(Platform(name="Google Maps"))

    for name in PROBLEM_CATEGORIES:
        if db.scalar(select(ProblemCategory).where(ProblemCategory.name == name)) is None:
            db.add(ProblemCategory(name=name))

    db.commit()
