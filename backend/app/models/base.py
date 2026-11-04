"""Base declarativa y mixins compartidos por las entidades ORM."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Raíz de la jerarquía declarativa de SQLAlchemy 2.0."""


def utc_now() -> datetime:
    """Instante actual en UTC, usado como default de las columnas de fecha."""
    return datetime.now(UTC)


class TimestampMixin:
    """Agrega ``created_at`` a las entidades que auditan su creación."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
