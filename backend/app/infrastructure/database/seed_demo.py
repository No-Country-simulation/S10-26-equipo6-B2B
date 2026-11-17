"""Script de población (seeding) de datos de demostración para RepuSense.

Genera >= 200 leads B2B calificados (< 3.5 estrellas, > 10 reseñas) con
reseñas negativas auténticas, análisis de IA y contactos enriquecidos.
Es 100% idempotente: si los registros ya existen, no los duplica.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.session import SessionLocal, init_db, seed_catalogs
from app.models import (
    AIAnalysis,
    Business,
    BusinessSource,
    Contact,
    Platform,
    ProblemCategory,
    Review,
    Search,
    SearchBusiness,
)

logger = logging.getLogger("repusense.seed")

# 8 Sectores y 8 Ciudades prioritarias de LatAm
SECTORS = [
    "clínicas dentales",
    "restaurantes",
    "talleres mecánicos",
    "hoteles boutique",
    "gimnasios",
    "veterinarias",
    "estéticas y spas",
    "academias de idiomas",
]

CITIES = [
    "Bogotá",
    "Medellín",
    "Ciudad de México",
    "Guadalajara",
    "Monterrey",
    "Buenos Aires",
    "Santiago",
    "Lima",
]

# Plantillas de nombres por sector (25 nombres únicos por sector = 200 leads en total)
NAMES_BY_SECTOR: dict[str, list[str]] = {
    "clínicas dentales": [
        "Clínica Dental OdontoSalud",
        "Centro Odontológico San Rafael",
        "Dental Sonrisas & Estética",
        "Clínica Odontológica DentalPlus",
        "Implantes & Sonrisas",
        "Odontología Integral Moderna",
        "Clínica Dental Innova",
        "OdontoCare Especialistas",
        "Centro Dental Las Américas",
        "Sonrisas Radiantes Dental",
        "Clínica Dental Alianza",
        "OdontoExpress Metropolitano",
        "Centro de Ortodoncia Providencia",
        "Clínica Dental Santa María",
        "Dental Corp Especialidades",
        "OdontoVida Familiar",
        "Clínica Dental Bellavista",
        "Centro Odontológico del Valle",
        "Clínica Dental Andes",
        "OdontoEstética Avanzada",
        "Clínica Dental El Bosque",
        "Especialistas Dentales Kennedy",
        "Centro Odontológico Las Condes",
        "Clínica Dental Los Cedros",
        "Odontología Láser & Estética",
    ],
    "restaurantes": [
        "Restaurante La Casona Gourmet",
        "Trattoria Bella Napoli",
        "Asador & Parrilla Criolla",
        "Bistró del Parque",
        "Marisquería El Timón",
        "Taquería Los Ahumados",
        "Fusión Wok & Grill",
        "Terraza Urbana Bistro",
        "Rincón Colonial Restaurante",
        "Parrilla Don Fernando",
        "Osteria del Puerto",
        "La Taberna Tradicional",
        "Restaurante Sabores del Valle",
        "Brasa & Leña Grill",
        "Cevichería Costa Brava",
        "El Jardín de las Delicias",
        "Pizzería Napolitana Artesanal",
        "La Estancia Asador",
        "Bistró Francés Saint Germain",
        "Restaurante Sabor Andino",
        "Cantina Don Juan",
        "Parrillada Los Leños",
        "Gourmet & Tradición",
        "Restaurante Mesón Real",
        "Mariscos & Pescados Don Pepe",
    ],
    "talleres mecánicos": [
        "Taller Mecánico MotorTech",
        "Frenos & Suspensión Express",
        "AutoTaller El Engranaje",
        "Mecánica Automotriz Precision",
        "ElectroAuto Integral",
        "Taller Diesel del Valle",
        "Servicio Técnico Multimarca Pro",
        "AutoClínica Mecánica",
        "Taller Automotriz Los Andes",
        "Inyección Electrónica Master",
        "Mecánica Rápida San Cristóbal",
        "AutoCentro del Norte",
        "Taller Mecánico El Pique",
        "ServiAuto Especialistas",
        "Taller Motores del Sur",
        "Alineación & Balanceo Total",
        "Clínica Automotriz Central",
        "Taller Mecánico La Tuerca",
        "Servicio Automotriz San Jorge",
        "AutoReparaciones Express",
        "Taller Mecánico Providencia",
        "Mecánica Integral del Oriente",
        "Taller AutoCheck",
        "Frenos & Embragues Metrópolis",
        "Mecánica General Don Carlos",
    ],
    "hoteles boutique": [
        "Hotel Boutique Villa Antigua",
        "Casona Colonial Suites",
        "Hotel Casa del Virrey",
        "Boutique Garden & Spa",
        "Hotel Magnolia Urbana",
        "Palacio San Miguel Suites",
        "EcoHotel Bosque Sagrado",
        "Hotel Vista Hermosa Boutique",
        "Casa Real Boutique Hotel",
        "Hotel Boutique Las Acacias",
        "Hostal Boutique Alameda",
        "Hotel Pasaje Colonial",
        "Quinta Escondida Boutique",
        "Hotel Bellavista Suites",
        "Casa Grande Boutique",
        "Hotel Rincón de la Colina",
        "Palacete de San Antonio",
        "Hotel Boutique Los Manantiales",
        "Villa Paraíso Boutique",
        "Hotel San Telmo Clásico",
        "Casa Morada Suites",
        "Hotel Boutique La Marquesa",
        "Casona San Isidro Hotel",
        "Hotel Boutique Terraza del Sol",
        "Residencia San Benito Hotel",
    ],
    "gimnasios": [
        "IronGym Fitness Center",
        "CrossPower Studio",
        "Gimnasio Titanes",
        "VitalFit Club",
        "Olimpo Cross Training",
        "FitZone Performance",
        "Athletic Club Central",
        "Box Training Metropolitano",
        "Gimnasio Fuerza & Salud",
        "PowerHouse Fitness Club",
        "Gimnasio Esparta",
        "Alpha Fitness Studio",
        "Centro de Entrenamiento Valkiria",
        "Gimnasio Fénix",
        "ActionFit Club",
        "Gimnasio Olympus Pro",
        "CrossFit Barrio Norte",
        "Club Deportivo Las Palmas",
        "Gimnasio Kronos",
        "EnergyFit Training Hub",
        "Gimnasio Los Conquistadores",
        "Maximus Training Gym",
        "Gimnasio Impacto",
        "Fitness & Salud 360",
        "UrbanBox Fitness Gym",
    ],
    "veterinarias": [
        "Clínica Veterinaria Mascotas Felices",
        "Hospital Veterinario San Francisco",
        "VetCare Urgencias & Cirugía",
        "Clínica Animalia",
        "Huellas & Garras Veterinaria",
        "Centro Médico Veterinario Integral",
        "Mundo Canino & Felino",
        "Veterinaria Los Alerces",
        "Hospital Veterinario 24 Horas",
        "Clínica Veterinaria San Lázaro",
        "PetSalud Centro Médico",
        "Veterinaria Las Rosas",
        "Amor Animal Veterinaria",
        "Clínica Veterinaria El Roble",
        "Atención Veterinaria San Roque",
        "VetExpress Urgencias",
        "Centro Veterinario La Colina",
        "Veterinaria Patitas & Colas",
        "Hospital Veterinario Metropolitano",
        "Clínica Veterinaria Alianza",
        "Veterinaria Santa Inés",
        "Centro de Especialidades Veterinarias",
        "Veterinaria San Bernardo",
        "BioVet Clínica Integral",
        "Veterinaria Providencia Animal",
    ],
    "estéticas y spas": [
        "Serenidad Spa & Bienestar",
        "Estética Velvet Salón",
        "Lumière Centro de Belleza",
        "Spa Urbano Armonía",
        "Glow Estética Integral",
        "DermoSalud & Spa",
        "Aura Belleza & Masajes",
        "Zen Vital Spa Urbano",
        "Salón & Spa Las Lilas",
        "Centro Estético Belleza Pura",
        "Oasis Spa & Relax",
        "Estética Facial Bella Donna",
        "Armonía & Estilo Spa",
        "Salón de Belleza Glamour",
        "Centro de Masajes San Lucas",
        "Spa & Masajes El Prado",
        "Clínica Estética Bellas Artes",
        "Salón & Spa Florencia",
        "Beauty & Harmony Studio",
        "Estética Médica Divina",
        "Spa Corporal Nirvana",
        "Centro de Belleza Miraflores",
        "Estética & Relax Los Laureles",
        "Spa Holístico Manantial",
        "Salón & Spa Magnolia",
    ],
    "academias de idiomas": [
        "Global Language Academy",
        "Instituto Británico del Norte",
        "English Fast Institute",
        "Polyglot Language Studio",
        "Academia Europea de Idiomas",
        "Oxford Learning Hub",
        "LinguaCenter Internacional",
        "SpeakUp Idiomas",
        "Instituto Anglo-Americano",
        "Berlitz & Oxford Training Center",
        "Academia Cambridge Language",
        "Centro de Idiomas Las Condes",
        "Instituto de Lenguas Modernas",
        "Master English Academy",
        "Focus Language School",
        "Academia de Idiomas El Trébol",
        "International English Hub",
        "Instituto Francés de Estudios",
        "Academia Alemana de Lenguas",
        "Universal Language Institute",
        "Global Talk Academia",
        "Instituto de Idiomas San Agustín",
        "English Today Institute",
        "Language & Culture Center",
        "Summit English Academy",
    ],
}

# Categorías maestras con sus quejas arquetípicas y plantillas de correo
REVIEWS_BY_CATEGORY: dict[str, list[tuple[int, str]]] = {
    "Atención al cliente": [
        (
            1,
            "Pésima atención del personal de recepción. Fueron sumamente groseros y "
            "no tuvieron la mínima disposición de ayudarme con un problema simple.",
        ),
        (
            2,
            "El trato hacia el cliente deja muchísimo que desear. Parece que estuvieran "
            "haciéndote un favor en lugar de brindar un servicio profesional.",
        ),
        (
            2,
            "Cero empatía del equipo comercial. Hice una consulta formal por WhatsApp y "
            "me dejaron en visto durante días sin responder mis dudas.",
        ),
        (
            1,
            "Mala actitud de los encargados. Cuando solicité hablar con un supervisor para "
            "exponer mi reclamo, simplemente se negaron a dar la cara.",
        ),
    ],
    "Demoras": [
        (
            1,
            "Tardaron más de 50 minutos en atenderme a pesar de que llegué puntual a mi "
            "cita agendada con días de anticipación. Muy impuntuales.",
        ),
        (
            2,
            "El tiempo de espera es excesivo. No dan explicaciones ni piden disculpas por "
            "los retrasos constantes que tienen en cada visita.",
        ),
        (
            2,
            "Prometieron una entrega en 48 horas y tardaron casi 10 días en terminar. "
            "Afectaron gravemente mi planificación por su falta de compromiso.",
        ),
        (
            1,
            "Filas interminables y una lentitud desesperante. Tienen muy poco personal para "
            "la cantidad de gente que reciben diariamente.",
        ),
    ],
    "Precios": [
        (
            1,
            "Cobran tarifas ocultas que jamás mencionan al inicio. El presupuesto final "
            "resultó ser casi el doble de lo acordado verbalmente.",
        ),
        (
            2,
            "Precios completamente desproporcionados para la calidad tan básica que ofrecen. "
            "No volvería a contratar sus servicios.",
        ),
        (
            2,
            "No entregan factura desglosada y se niegan a aclarar los conceptos cobrados. "
            "Poco transparente la gestión administrativa.",
        ),
        (
            1,
            "Penalizaciones abusivas en las cláusulas de pago sin previo aviso ni recibo claro. "
            "Sentí que me cobraron de más arbitrariamente.",
        ),
    ],
    "Higiene": [
        (
            1,
            "Las instalaciones se ven descuidadas y sucias. Los baños de clientes no "
            "tenían jabón ni toallas de papel y emanaban mal olor.",
        ),
        (
            2,
            "El instrumental y los espacios de atención no parecían esterilizados ni "
            "limpios. Da muy mala espina en cuanto a normas de salubridad.",
        ),
        (
            2,
            "Polvo acumulado en los rincones y basura sin recoger en la sala de espera. "
            "Falta supervisión urgente en la limpieza del local.",
        ),
        (
            1,
            "Desorden generalizado y aspecto descuidado en todas las áreas de atención. "
            "No cumple los estándares mínimos que uno espera de este rubro.",
        ),
    ],
}

EMAIL_TEMPLATES_BY_CATEGORY: dict[str, tuple[str, str, str]] = {
    "Atención al cliente": (
        "Atención insatisfecha y pérdida de clientes por trato en recepción",
        "Oportunidad de mejora en la experiencia de servicio de {nombre}",
        "Estimado equipo directivo de {nombre}: analizando las opiniones recientes de sus "
        "clientes en Google Maps, notamos varias menciones críticas sobre la atención al "
        "cliente y fricciones en recepción que impactan su calificación ({rating}★). En "
        "RepuSense ayudamos a negocios de {sector} a optimizar protocolos de servicio y "
        "recuperar clientes disconformes antes de que dejen una reseña negativa pública.",
    ),
    "Demoras": (
        "Tiempos de espera excesivos e impuntualidad en citas y entregas",
        "Optimización de tiempos de atención y flujo de clientes en {nombre}",
        "Estimado equipo directivo de {nombre}: al revisar las reseñas de Google de su sede "
        "en {city}, detectamos que el 60% del descontento de sus clientes se origina en "
        "demoras y largos tiempos de espera, afectando su reputación digital ({rating}★). "
        "Nuestra solución especializada para {sector} automatiza el agendamiento y la "
        "comunicación preventiva para proteger su calificación en Google.",
    ),
    "Precios": (
        "Descontento por cobros inesperados y falta de claridad presupuestaria",
        "Estrategia para transparentar presupuestos y fidelizar clientes en {nombre}",
        "Estimado equipo directivo de {nombre}: observamos en las valoraciones recientes "
        "de Google que varios usuarios reportan dudas sobre tarifas y claridad en cobros, "
        "lo que sitúa su promedio en {rating}★. Ayudamos a empresas líderes de {sector} a "
        "diseñar presupuestos transparentes y programas de fidelización que transforman "
        "opiniones dudosas en promotores de marca.",
    ),
    "Higiene": (
        "Percepción negativa sobre mantenimiento e higiene de las instalaciones",
        "Propuesta para elevar los estándares percibidos de calidad en {nombre}",
        "Estimado equipo directivo de {nombre}: tras analizar la retroalimentación de sus "
        "clientes en Google Maps, identificamos alertas reiteradas relacionadas con el "
        "estado y mantenimiento de sus instalaciones ({rating}★). Ponemos a su disposición "
        "auditorías de satisfacción rápida y gestión de reputación para consolidar la "
        "confianza de quienes visitan {nombre}.",
    ),
}

AUTHORS = [
    "Camila Fernández",
    "Javier Morales",
    "Valentina Silva",
    "Matías Rojas",
    "Lucía Mendoza",
    "Andrés Herrera",
    "Mariana Castillo",
    "Gabriel Vargas",
    "Daniela Ortiz",
    "Felipe Navarro",
    "Paula Benítez",
    "Diego Paredes",
    "Sofía Guzmán",
    "Esteban Castro",
    "Natalia Reyes",
    "Rodrigo Muñoz",
]


def _crear_slug(texto: str) -> str:
    """Convierte un nombre comercial en slug para dominio web y email."""
    limpio = (
        texto.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .replace("&", "y")
    )
    tokens = [c if c.isalnum() else "-" for c in limpio]
    return "".join(tokens).strip("-")[:40]


def seed_demo_data(db: Session, max_leads: int = 200) -> dict[str, int]:
    """Puebla de forma idempotente la base de datos con >= 200 leads B2B calificados.

    Args:
        db: Sesión de SQLAlchemy activa.
        max_leads: Número máximo de prospectos a sembrar (por defecto 200).

    Returns:
        Diccionario con conteos de registros sembrados o existentes.
    """
    seed_catalogs(db)

    platform = db.scalar(select(Platform).where(Platform.name == "Google Maps"))
    if platform is None:
        raise RuntimeError("No se encontró la plataforma maestra 'Google Maps'.")

    # Mapeo de categorías maestras
    categorias_db = {cat.name: cat for cat in db.scalars(select(ProblemCategory)).all()}
    cat_keys = list(REVIEWS_BY_CATEGORY.keys())

    creados = 0
    existentes = 0
    contador = 0

    now = datetime.now(UTC)

    # Creamos o recuperamos una búsqueda por cada (sector, ciudad)
    searches_cache: dict[tuple[str, str], Search] = {}

    for sector in SECTORS:
        nombres = NAMES_BY_SECTOR[sector]
        for idx_en_sector, nombre in enumerate(nombres):
            if contador >= max_leads:
                break
            contador += 1

            ciudad = CITIES[idx_en_sector % len(CITIES)]
            external_id = f"ChIJ_seed_{contador:04d}"

            # Verificación de idempotencia
            fuente_existente = db.scalar(
                select(BusinessSource).where(
                    BusinessSource.platform_id == platform.platform_id,
                    BusinessSource.external_id == external_id,
                )
            )
            if fuente_existente is not None:
                existentes += 1
                continue

            # Gestión de Search para trazabilidad
            search_key = (sector, ciudad)
            if search_key not in searches_cache:
                search = db.scalar(
                    select(Search).where(
                        Search.sector == sector,
                        Search.city == ciudad,
                    )
                )
                if search is None:
                    search = Search(
                        sector=sector,
                        city=ciudad,
                        max_rating=Decimal("3.5"),
                        min_reviews=10,
                        status="FINISHED",
                        started_at=now - timedelta(days=2),
                        finished_at=now - timedelta(days=2, minutes=-5),
                    )
                    db.add(search)
                    db.flush()
                searches_cache[search_key] = search

            search = searches_cache[search_key]

            # Parámetros del lead: rating entre 2.2 y 3.4, reviews entre 14 y 78
            rating_val = round(2.2 + ((contador * 7) % 13) * 0.1, 1)
            total_revs = 14 + ((contador * 11) % 65)

            # Distribución de estados: ~80% NEW, ~12% CONTACTED, ~8% DISCARDED
            if contador % 8 == 0:
                lead_status = "CONTACTED"
                contacted_at = now - timedelta(days=(contador % 15) + 1)
            elif contador % 13 == 0:
                lead_status = "DISCARDED"
                contacted_at = None
            else:
                lead_status = "NEW"
                contacted_at = None

            slug = _crear_slug(nombre)
            dominio = f"{slug}.com"
            telefono = f"+54 9 11 {4000 + contador}-{1000 + contador}"

            business = Business(
                business_id=uuid4(),
                name=nombre,
                sector=sector,
                city=ciudad,
                address=f"Av. Principal #{100 + contador}, {ciudad}",
                phone_number=telefono,
                website=dominio,
                lead_status=lead_status,
                contacted_at=contacted_at,
            )
            db.add(business)
            db.flush()

            # Relación N:M Search <-> Business
            db.add(
                SearchBusiness(
                    search_id=search.search_id,
                    business_id=business.business_id,
                    found_at=now - timedelta(days=1),
                )
            )

            # Ficha de plataforma
            source = BusinessSource(
                business_id=business.business_id,
                platform_id=platform.platform_id,
                external_id=external_id,
                source_url=f"https://maps.google.com/?cid={1000000000 + contador}",
                rating=Decimal(str(rating_val)),
                total_reviews=total_revs,
                last_scraped_at=now - timedelta(days=1),
            )
            db.add(source)
            db.flush()

            # Reseñas negativas: seleccionamos una categoría principal
            cat_name = cat_keys[contador % len(cat_keys)]
            cat_obj = categorias_db[cat_name]
            plantillas_resenas = REVIEWS_BY_CATEGORY[cat_name]

            for r_idx, (r_rating, r_text) in enumerate(plantillas_resenas):
                autor = AUTHORS[(contador + r_idx) % len(AUTHORS)]
                rev_date = now - timedelta(days=(r_idx + 1) * 6 + (contador % 5))
                review = Review(
                    business_source_id=source.business_source_id,
                    external_id=f"rev_{external_id}_{r_idx + 1}",
                    author=autor,
                    rating=r_rating,
                    content=r_text,
                    reviewed_at=rev_date,
                    scraped_at=now - timedelta(days=1),
                )
                db.add(review)

            # Análisis de IA pre-calculado
            pain_summary, subject_tpl, body_tpl = EMAIL_TEMPLATES_BY_CATEGORY[cat_name]
            subject = subject_tpl.format(nombre=nombre)
            first_para = body_tpl.format(
                nombre=nombre,
                rating=rating_val,
                sector=sector,
                city=ciudad,
            )

            ai_analysis = AIAnalysis(
                business_id=business.business_id,
                problem_category_id=cat_obj.problem_category_id,
                pain_points_summary=pain_summary,
                email_subject=subject,
                email_first_paragraph=first_para,
                ai_model="gemini-1.5-flash-prospector",
                generated_at=now - timedelta(hours=12),
            )
            db.add(ai_analysis)

            # Contacto enriquecido (RF3)
            db.add(
                Contact(
                    business_id=business.business_id,
                    contact_type="EMAIL",
                    value=f"contacto@{dominio}",
                    source="WEBSITE",
                )
            )
            creados += 1

    db.commit()
    logger.info("Seeding demo finalizado: %d creados, %d existentes.", creados, existentes)
    return {"creados": creados, "existentes": existentes}


def main() -> None:
    """CLI para ejecutar el seeding directamente."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    init_db()
    with SessionLocal() as db:
        res = seed_demo_data(db, max_leads=200)
        print(f"Resultado del Seeding: {res['creados']} creados, {res['existentes']} existentes.")


if __name__ == "__main__":
    main()
