"""Repositorio de negocios, fichas de plataforma y su idempotencia (RNF3)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Business, BusinessSource, Platform, SearchBusiness
from app.schemas.discovery import Negocio


class BusinessRepository:
    """Persistencia de ``business`` y ``business_source``."""

    model = Business

    def get(self, db: Session, entity_id: UUID) -> Business | None:
        return self.get_by_id(db, entity_id)

    def get_by_id(self, db: Session, business_id: UUID) -> Business | None:
        return db.get(Business, business_id)

    def ensure_platform(self, db: Session, name: str = "Google Maps") -> Platform:
        """Devuelve la plataforma por nombre, creándola si el catálogo está vacío."""
        platform = db.scalar(select(Platform).where(Platform.name == name))
        if platform is None:
            platform = Platform(name=name)
            db.add(platform)
            db.flush()
        return platform

    def upsert_from_discovery(
        self,
        db: Session,
        negocio: Negocio,
        platform_id: int,
    ) -> BusinessSource:
        """Inserta o actualiza la ficha ``(platform_id, external_id)``.

        En PostgreSQL la escritura se resuelve con ``ON CONFLICT DO UPDATE``
        sobre la restricción única de RNF3. El fallback permite ejecutar los
        tests con SQLite sin cambiar el contrato del método.
        """
        now = datetime.now(UTC)
        external_id = negocio.place_id

        existente = db.scalar(
            select(BusinessSource).where(
                BusinessSource.platform_id == platform_id,
                BusinessSource.external_id == external_id,
            )
        )
        if existente is not None:
            business = db.get(Business, existente.business_id)
            if business is not None:
                self._update_business(business, negocio)
            self._update_source(existente, negocio, now)
            db.flush()
            return existente

        business = self._find_matching_business(db, negocio)
        if business is None:
            business = Business(
                name=negocio.nombre,
                sector=negocio.rubro,
                address=negocio.direccion,
                phone_number=negocio.telefono,
                website=negocio.website,
                lead_status="NEW",
            )
            db.add(business)
            db.flush()
        else:
            self._update_business(business, negocio)

        valores = self._source_values(business.business_id, platform_id, negocio, now)

        if db.get_bind().dialect.name == "postgresql":
            statement = (
                pg_insert(BusinessSource)
                .values(**valores)
                .on_conflict_do_update(
                    constraint="uq_business_source_platform_external",
                    set_={
                        "source_url": valores["source_url"],
                        "rating": valores["rating"],
                        "total_reviews": valores["total_reviews"],
                        "last_scraped_at": valores["last_scraped_at"],
                    },
                )
                .returning(BusinessSource)
            )
            source = db.execute(statement).scalar_one()
            db.flush()
            return source

        source = BusinessSource(**valores)
        db.add(source)
        db.flush()
        return source

    def enrich_search_context(
        self,
        db: Session,
        business_id: UUID,
        sector: str | None = None,
        city: str | None = None,
    ) -> Business | None:
        """Completa sector/ciudad con los parámetros de la búsqueda que lo halló."""
        business = self.get_by_id(db, business_id)
        if business is None:
            return None
        if sector:
            business.sector = sector
        if city:
            business.city = city
        db.flush()
        return business

    def update_lead_status(
        self,
        db: Session,
        business_id: UUID,
        lead_status: str,
    ) -> Business | None:
        """Actualiza el estado comercial y registra el primer contacto."""
        business = self.get_by_id(db, business_id)
        if business is None:
            return None
        business.lead_status = lead_status
        if lead_status == "CONTACTED" and business.contacted_at is None:
            business.contacted_at = datetime.now(UTC)
        db.flush()
        return business

    def list_leads(
        self,
        db: Session,
        search_id: UUID | None,
        city: str | None,
        sector: str | None,
        lead_status: str | None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Business], int]:
        """Lista leads paginados con filtros dinámicos y su total."""
        page = max(page, 1)
        page_size = max(page_size, 1)

        filtros = []
        if city:
            filtros.append(Business.city == city)
        if sector:
            filtros.append(Business.sector == sector)
        if lead_status:
            filtros.append(Business.lead_status == lead_status.upper())

        consulta = select(Business)
        conteo = select(func.count(func.distinct(Business.business_id)))
        if search_id is not None:
            union = SearchBusiness.business_id == Business.business_id
            consulta = consulta.join(SearchBusiness, union)
            conteo = conteo.join(SearchBusiness, union)
        if filtros:
            consulta = consulta.where(*filtros)
            conteo = conteo.where(*filtros)

        consulta = (
            consulta.options(selectinload(Business.sources))
            .order_by(Business.created_at.desc(), Business.business_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        items = list(db.scalars(consulta).unique())
        total = int(db.scalar(conteo) or 0)
        return items, total

    def _find_matching_business(self, db: Session, negocio: Negocio) -> Business | None:
        consulta = select(Business).where(Business.name == negocio.nombre)
        if negocio.direccion:
            consulta = consulta.where(Business.address == negocio.direccion)
        return db.scalars(consulta.limit(1)).first()

    def _update_business(self, business: Business, negocio: Negocio) -> None:
        business.name = negocio.nombre
        if negocio.rubro:
            business.sector = negocio.rubro
        if negocio.direccion:
            business.address = negocio.direccion
        if negocio.telefono:
            business.phone_number = negocio.telefono
        if negocio.website:
            business.website = negocio.website

    def _update_source(
        self,
        source: BusinessSource,
        negocio: Negocio,
        now: datetime,
    ) -> None:
        source.source_url = self._build_source_url(negocio.place_id)
        source.rating = Decimal(str(negocio.rating))
        source.total_reviews = negocio.total_resenas
        source.last_scraped_at = now

    def _source_values(
        self,
        business_id: UUID,
        platform_id: int,
        negocio: Negocio,
        now: datetime,
    ) -> dict:
        return {
            "business_id": business_id,
            "platform_id": platform_id,
            "external_id": negocio.place_id,
            "source_url": self._build_source_url(negocio.place_id),
            "rating": Decimal(str(negocio.rating)),
            "total_reviews": negocio.total_resenas,
            "last_scraped_at": now,
        }

    def _build_source_url(self, external_id: str) -> str:
        return f"https://www.google.com/maps/place/?q=place_id:{external_id}"
