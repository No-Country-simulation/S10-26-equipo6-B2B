# RepuSense — Radar de Reputación en Crisis

> **NoCountry · Simulación Laboral Abierta**
> Marketing Digital / Relaciones Públicas (B2B SaaS) — Prospección automatizada

RepuSense es un motor de prospección que detecta negocios locales con mala reputación en
internet, extrae sus datos de contacto y prepara el correo en frío para el equipo de ventas.

---

## El problema

La empresa es una agencia de relaciones públicas y marketing digital enfocada en ayudar a
pequeñas y medianas empresas —restaurantes, clínicas, servicios locales— a recuperar su
reputación en internet y mitigar el impacto de campañas de difamación o malas rachas de servicio.

Hoy, el cuello de botella es la **prospección comercial**:

| | |
|---|---|
| Equipo comercial | **3 vendedores** |
| Dedica | **~30 horas semanales** a búsqueda manual |
| Plataformas | Google Maps, TripAdvisor y Yelp |
| Filtro | negocios con entre **1.5 y 3.5 estrellas** |
| Luego | leen las reseñas para confirmar que el negocio sigue operando y buscan el contacto en la web o redes sociales del local |
| Producción actual | **40 leads semanales** |
| Meta | **cientos de contactos calificados** |

Este proceso manual es lento, desmotivador para el equipo de ventas y altamente ineficiente.

### La necesidad

Automatizar la detección de negocios locales con baja calificación, extraer sus datos básicos de
contacto y centralizar la información para que el equipo de ventas prospecte de forma ágil,
masiva y segmentada.

---

## Qué construimos

Un pipeline de extracción de datos que recibe una **ciudad** y un **rubro** —por ejemplo,
«clínicas dentales en Bogotá»— y recolecta los negocios que cumplen las reglas de negocio:
**menos de 3.5 estrellas y más de 10 reseñas**.

### Flujo funcional

```
Input            Ciudad + Rubro + filtros (< 3.5 ★, > 10 reseñas)
  │
  ▼
Scraper          nombre · rating · nº de reseñas · últimas 5 reseñas
                 negativas · teléfono · web
  │
  ▼
Enriquec. IA     el LLM lee las últimas 5 reseñas negativas y etiqueta
                 el problema principal: atención · precios · higiene · demoras
  │
  ▼
Enriquec. dato   scraping web del negocio → email
                 búsqueda de perfil de LinkedIn
  │
  ▼
Dashboard        tabla con filtros por calificación, problema detectado,
                 ciudad y estado del lead · exportar CSV · copiar draft
  │
  ▼
Diferenciador    genera automáticamente el asunto + primer párrafo
                 del correo en frío, basado en las quejas reales
```

---

## Entregables esperados

1. **Motor de extracción funcional** — script, API o pipeline que reciba parámetros
   (rubro, ubicación) y devuelva un listado de negocios afectados de una plataforma.

2. **Interfaz de prospección (Dashboard)** — web app interna donde el vendedor lance
   búsquedas, vea los leads en tabla con filtros por calificación y acceda a los datos
   de contacto encontrados.

3. **Base de datos poblada** — al menos **200 leads reales** extraídos durante las pruebas,
   para demostrar el valor del producto en el Demo Day.

4. **Feature diferenciador (IA)** — generación automática de un *asunto* y un *primer párrafo*
   para un correo en frío, redactado por IA sobre las quejas específicas que el scraper
   encontró en las reseñas del negocio.

---

## Los tres desafíos

| # | Desafío | Pregunta abierta |
|---|---------|------------------|
| 1 | **Bloqueos y recolección eficiente** | Google Maps y Yelp tienen políticas anti-bot estrictas. ¿Cómo se estructura el scraper —rotación de IPs, tiempos de espera, headless browsers— para extraer cientos de negocios diarios sin ser bloqueado a los 10 minutos, en un MVP sin presupuesto para proxies premium? |
| 2 | **El dato de contacto (enriquecimiento)** | Los directorios de reseñas rara vez muestran el correo del dueño; a lo sumo un teléfono genérico o una web. ¿Qué estrategia cruza el negocio encontrado con un email o perfil de LinkedIn válido de forma automatizada? |
| 3 | **Estado y duplicidad** | Si el vendedor corre «Restaurantes en CDMX» esta semana y vuelve a correrla la próxima, ¿cómo se diseña el modelo de datos para actualizar las calificaciones en vez de crear leads duplicados que hagan que un mismo cliente reciba dos correos idénticos? |

---

## Stack oficial del proyecto

| Capa | Tecnología | Detalle |
|------|------------|---------|
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · Lucide | Dashboard comercial, pipeline de prospectos, búsqueda en tiempo real y exportación RFC 4180 |
| Backend | Python 3.12 · FastAPI · Pydantic v2 | Monolito por capas (Layered Monolith) concéntrico y tipado estricto |
| Persistencia | PostgreSQL 16 · SQLAlchemy 2 · SQLite (in-memory tests) | Modelo relacional de 9 tablas normalizadas con restricciones de unicidad e idempotencia |
| Procesamiento Asíncrono | Redis 7 · Worker desacoplado | Encolamiento con fallback síncrono para despliegues ligeros |
| IA & NLP | LLM Client · Catálogo controlado de problemas | Clasificador de reseñas, resumen de quejas y generador de cold email con escudo anti-alucinación |
| Testing & Linter | Pytest · Ruff · Oxlint · TypeScript | Suite completa de 139 tests unitarios, de contrato y arquitectura al 100% |

---

## Estado de los entregables del MVP

| | Entregable | Estado | Detalle |
|---|---|---|---|
| ✅ | **1 · Motor de extracción funcional** | **COMPLETO** | Discovery vía SerpApi Google Maps y extracción anónima de reseñas negativas (`rating <= 3`) en [`backend/app/services/`](backend/app/services/). |
| ✅ | **2 · Dashboard de prospección (Web)** | **COMPLETO** | Web app en React 19 con filtros, pipeline CRM, detalle de prospectos, regeneración con IA y exportación a CSV ([#84](https://github.com/No-Country-simulation/S10-26-equipo6-B2B/pull/84), [#86](https://github.com/No-Country-simulation/S10-26-equipo6-B2B/pull/86)). |
| ✅ | **3 · Base de datos con ≥ 200 leads reales** | **COMPLETO** | Script idempotente con 200 leads calificados en 8 sectores y 8 ciudades de LatAm, con reseñas críticas, análisis de IA y contactos ([#88](https://github.com/No-Country-simulation/S10-26-equipo6-B2B/pull/88)). Ejecutable vía `pnpm seed`. |
| ✅ | **4 · Feature diferenciador de IA** | **COMPLETO** | Inferencia con catálogo controlado (`problem_category`), redactor de cold email personalizado (asunto y primer párrafo) y escudo anti-alucinación ([#74](https://github.com/No-Country-simulation/S10-26-equipo6-B2B/pull/74)). |

---

## Cómo ejecutar el proyecto

### 1. Desarrollo local rápido (Monorepo)

```bash
# 1. Instalar dependencias
pnpm install

# 2. Levantar base de datos y cache en Docker (opcional, o usar SQLite para tests)
docker compose up -d

# 3. Poblar los 200 leads calificados para la Demo
pnpm seed

# 4. Levantar Backend (FastAPI :8000) y Frontend (Vite :5173) en paralelo
pnpm dev:local
```

Visita `http://localhost:5173` para acceder al dashboard comercial y `http://localhost:8000/docs` para la documentación interactiva Swagger de la API.

### 2. Despliegue completo con Docker Compose

```bash
# Levantar PostgreSQL, Redis, Backend y Worker en contenedores:
docker compose --profile full up -d --build
```

---

## Estructura del repositorio

```
├── .github/
│   ├── workflows/            Pipeline de Quality Gate continuo (CI)
│   ├── ISSUE_TEMPLATE/       Plantillas de bug y feature
│   └── pull_request_template.md
├── backend/
│   ├── app/                  Layered Monolith (api, services, repositories, models, infrastructure)
│   │   ├── etl/              CLI de reseñas y smoke test de QA
│   │   └── worker.py         Proceso worker desacoplado para tareas de Redis
│   └── tests/                Suite de 110 pruebas unitarias, de contrato y arquitectura
├── frontend/
│   └── src/                  Dashboard en React 19 + TypeScript + Vite
├── docs/
│   ├── CONTRIBUTING.md       Guía de contribución y flujo de revisión
│   ├── systemDesign.md       Diseño de sistema, ERD de 9 tablas y flujos
│   ├── Diccionario_de_tablas_y_campos.md  Diccionario de datos normalizado
│   └── fuente-de-resenas.md  Contrato del endpoint y evidencia de verificación
├── docker-compose.yml        Infraestructura local (PostgreSQL 16, Redis 7 y Worker)
└── AGENTS.md                 Directrices arquitectónicas oficiales y protocolo anti-alucinación
```

---

## Contribuir

Leé [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) antes de abrir un PR: convenciones de
commits, etiquetas de issue y el checklist de revisión.
