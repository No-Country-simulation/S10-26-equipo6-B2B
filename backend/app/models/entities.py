"""Las nueve entidades del ERD validado de RepuSense.

El modelo sigue ``docs/Diccionario_de_tablas_y_campos.md`` y las restricciones
declaradas en ``docs/systemDesign.md`` (sección 3.3). Las claves son UUID
genéricos de SQLAlchemy para que el mismo modelo funcione en PostgreSQL y en
SQLite durante las pruebas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now


class Platform(Base):
    """Catálogo maestro de plataformas de origen (Google Maps, Yelp, ...)."""

    __tablename__ = "platform"

    platform_id: Mapped[int] = mapped_column(
        SmallInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    sources: Mapped[list[BusinessSource]] = relationship(back_populates="platform")


class Search(Base, TimestampMixin):
    """Una ejecución de prospección y su estado asíncrono."""

    __tablename__ = "search"

    search_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    max_rating: Mapped[Decimal] = mapped_column(
        Numeric(2, 1), default=Decimal("3.5"), nullable=False
    )
    min_reviews: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    business_links: Mapped[list[SearchBusiness]] = relationship(
        back_populates="search",
        cascade="all, delete-orphan",
    )


class Business(Base, TimestampMixin):
    """El lead comercial, independiente de la plataforma donde se encontró."""

    __tablename__ = "business"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_status: Mapped[str] = mapped_column(String(30), default="NEW", nullable=False)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    search_links: Mapped[list[SearchBusiness]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )
    sources: Mapped[list[BusinessSource]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )
    contacts: Mapped[list[Contact]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )
    ai_analysis: Mapped[AIAnalysis] = relationship(
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SearchBusiness(Base):
    """Relación N:M entre una búsqueda y los negocios que encontró."""

    __tablename__ = "search_business"

    search_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("search.search_id", ondelete="CASCADE"),
        primary_key=True,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("business.business_id", ondelete="CASCADE"),
        primary_key=True,
    )
    found_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    search: Mapped[Search] = relationship(back_populates="business_links")
    business: Mapped[Business] = relationship(back_populates="search_links")


class BusinessSource(Base):
    """Ficha de un negocio en una plataforma concreta."""

    __tablename__ = "business_source"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "external_id",
            name="uq_business_source_platform_external",
        ),
    )

    business_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("business.business_id"),
        nullable=False,
    )
    platform_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("platform.platform_id"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)
    total_reviews: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped[Business] = relationship(back_populates="sources")
    platform: Mapped[Platform] = relationship(back_populates="sources")
    reviews: Mapped[list[Review]] = relationship(
        back_populates="business_source",
        cascade="all, delete-orphan",
    )


class Review(Base):
    """Reseña individual extraída de una ficha de plataforma."""

    __tablename__ = "review"
    __table_args__ = (
        UniqueConstraint(
            "business_source_id",
            "external_id",
            name="uq_review_source_external",
        ),
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("business_source.business_source_id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(150), nullable=True)
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    business_source: Mapped[BusinessSource] = relationship(back_populates="reviews")


class ProblemCategory(Base):
    """Catálogo controlado de problemas que puede asignar el LLM."""

    __tablename__ = "problem_category"

    problem_category_id: Mapped[int] = mapped_column(
        SmallInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    analyses: Mapped[list[AIAnalysis]] = relationship(back_populates="problem_category")


class AIAnalysis(Base):
    """Resultado de la inferencia del LLM para un negocio."""

    __tablename__ = "ai_analysis"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("business.business_id"),
        unique=True,
        nullable=False,
    )
    problem_category_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("problem_category.problem_category_id"),
        nullable=False,
    )
    pain_points_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_first_paragraph: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    business: Mapped[Business] = relationship(back_populates="ai_analysis")
    problem_category: Mapped[ProblemCategory] = relationship(back_populates="analyses")


class Contact(Base, TimestampMixin):
    """Dato de contacto encontrado durante el enriquecimiento."""

    __tablename__ = "contact"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("business.business_id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    business: Mapped[Business] = relationship(back_populates="contacts")
