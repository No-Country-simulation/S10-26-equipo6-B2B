# RepuSense

Motor de prospección B2B que detecta negocios locales con problemas de reputación online, extrae sus datos de contacto y genera propuestas comerciales personalizadas basadas en quejas reales de sus clientes.

Proyecto desarrollado para el track B2B SaaS en la simulación laboral de **NoCountry**.

---

## El problema que resuelve

Para una agencia de marketing digital o relaciones públicas, los mejores prospectos son aquellos que sufren un dolor evidente: negocios locales con calificaciones bajas en Google Maps (< 3.5 estrellas) que pierden clientes todos los días debido a mala atención, demoras o precios confusos.

Hacer esta prospección a mano es insostenible:
* Un equipo de 3 vendedores invierte cerca de 30 horas semanales buscando locales uno por uno en mapas.
* Tienen que entrar al perfil, calcular el rating, leer reseñas para entender qué falla, buscar la página web del local e intentar encontrar un correo de contacto.
* El rendimiento apenas alcanza unos 40 leads semanales por persona.

**RepuSense automatiza todo ese ciclo en segundos:** el vendedor solo ingresa una ciudad y un rubro (por ejemplo, *«clínicas dentales en Bogotá»* o *«restaurantes en Guadalajara»*), y el sistema le entrega un listado calificado con contactos, resumen de quejas y un borrador de correo listo para contactar.

---

## Cómo funciona el pipeline

```
  [Ciudad + Rubro] (< 3.5★, > 10 reseñas)
         │
         ▼
  1. Discovery & Filtrado      -> Detecta locales que cumplen los filtros de negocio
         │
         ▼
  2. Extracción de Reseñas     -> Obtiene las 5 reseñas negativas más recientes (rating <= 3)
         │
         ▼
  3. Clasificación con IA      -> Etiqueta el problema raíz (Atención, Demoras, Precios, Higiene)
         │                        y redacta el gancho comercial (asunto + 1er párrafo)
         ▼
  4. Enriquecimiento Web       -> Rastrea la web oficial para extraer correos y teléfonos
         │
         ▼
  5. Dashboard Comercial       -> Vista de gestión en React: pipeline CRM, filtros y exportación a CSV
```

### Decisiones de ingeniería destacadas

1. **Extracción ligera sin navegadores pesados:** En lugar de levantar instancias de Puppeteer/Selenium que consumen memoria y son bloqueadas por Cloudflare/Google en pocos minutos, el módulo de reseñas consulta directamente el protocolo RPC anónimo que usa Google Maps en su versión web (`GetLocalBoqProxy`). Extrae 100 reseñas en menos de 7 segundos con cero costo de infraestructura.
2. **Idempotencia y anti-duplicados:** El modelo relacional utiliza una restricción única por `(platform_id, external_id)`. Si el equipo busca el mismo rubro semanas después, el sistema actualiza calificaciones y reseñas en lugar de duplicar leads en la base de datos.
3. **Escudo anti-alucinación en IA:** El clasificador de reseñas utiliza un catálogo cerrado de categorías y valida las respuestas del LLM con Pydantic. Si el modelo genera texto fuera de las quejas reales o no hay conexión con OpenAI/Gemini, entra en juego un motor heurístico offline que garantiza que el sistema nunca se detenga.
4. **Arquitectura desacoplada (Layered Monolith):** El backend sigue una estructura concéntrica en cuatro capas: Presentación (`api`), Casos de uso (`services`), Persistencia (`repositories` y `models`) e Infraestructura (`infrastructure`). Toda dependencia externa cumple protocolos tipados (DIP).

---

## Stack técnico

* **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (ORM con tipado estricto `Mapped[...]`), Pydantic v2.
* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons.
* **Persistencia & Cache:** PostgreSQL 16, Redis 7 (con fallback SQLite en memoria para tests unitarios).
* **Gestión de paquetes & Monorepo:** Turborepo, pnpm (workspace Node), uv (entorno Python ultrarrápido).
* **Calidad de código:** Pytest (139 tests), Ruff (linter/formatter Python), Oxlint (linter JS/TS).

---

## Puesta en marcha

### Requisitos previos
* Node.js >= 20 y `pnpm` (`npm install -g pnpm`)
* Python >= 3.12 y `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh` o en Windows `irm https://astral.sh/uv/install.ps1 | iex`)
* Docker y Docker Compose (opcional para persistencia completa)

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/No-Country-simulation/S10-26-equipo6-B2B.git
cd S10-26-equipo6-B2B

# Instala dependencias del monorepo y del backend
pnpm install
cd backend && uv sync --frozen --group dev && cd ..
```

### 2. Configurar variables de entorno

Copia los archivos de ejemplo:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

*(Opcional: Si tienes una API key de SerpApi o de OpenAI, colócalas en `backend/.env`. Si no las tienes, el sistema opera con datos de demostración y motor de IA heurístico offline).*

### 3. Cargar datos de demostración (Demo Day)

El proyecto incluye un script de siembra con **200 leads B2B reales** distribuidos en 8 rubros y 8 ciudades de Latinoamérica con reseñas negativas, análisis de IA y correos corporativos:

```bash
pnpm seed
```

### 4. Levantar la aplicación en modo desarrollo

Inicia simultáneamente el backend en FastAPI y el frontend en Vite:

```bash
pnpm dev:local
```

* **Frontend:** [http://localhost:5173](http://localhost:5173)
* **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Despliegue con Docker

Para levantar toda la infraestructura (PostgreSQL, Redis, Backend y Worker) en contenedores:

```bash
# Levantar base de datos y Redis
docker compose up -d

# O levantar el stack completo
docker compose --profile full up -d --build
```

---

## Estado de los entregables del MVP

| Entregable | Estado | Descripción técnica |
|---|---|---|
| **1. Motor de extracción** | Terminado | Discovery con SerpApi Google Maps y extractor anónimo de reseñas críticas en `backend/app/services/prospecting_service.py`. |
| **2. Dashboard web comercial** | Terminado | Interfaz React 19 con filtros en tiempo real, pipeline de prospección (Nuevo / Contactado / Descartado), vista de detalle con reseñas y exportación a CSV (RFC 4180). |
| **3. Base de datos con ≥ 200 leads** | Terminado | Base de datos relacional de 9 tablas con 200 leads calificados en 8 sectores prioritarios y 8 ciudades de LatAm, ejecutable mediante `pnpm seed`. |
| **4. Feature diferenciador de IA** | Terminado | Clasificador automático de quejas recurrentes, extractor de puntos de dolor y redactor de cold email (asunto y primer párrafo) con mitigación de alucinaciones. |

---

## Calidad y tests

El repositorio cuenta con una suite automatizada de pruebas y linters que se ejecuta en cada Pull Request mediante GitHub Actions:

```bash
# Ejecutar linter en frontend y backend
pnpm lint

# Ejecutar suite completa de pruebas unitarias y de arquitectura (139 tests)
pnpm test
```

---

## Estructura del monorepo

```
├── backend/
│   ├── app/
│   │   ├── api/             Controladores FastAPI versionados (v1) y DTOs Pydantic
│   │   ├── services/        Lógica de prospección, análisis IA y enriquecimiento
│   │   ├── repositories/    Consultas y operaciones idempotentes en base de datos
│   │   ├── models/          Definición ORM de las 9 tablas (SQLAlchemy)
│   │   ├── infrastructure/  Clientes HTTP externos, colas Redis y scripts de base de datos
│   │   └── etl/             CLI de extracción y pruebas de humo para QA
│   └── tests/               139 pruebas unitarias, de integración y arquitectura
├── frontend/
│   └── src/
│       ├── components/      Componentes visuales (tablas, cards, métricas)
│       ├── pages/           Vistas de búsqueda, prospectos y detalle de lead
│       ├── services/        Cliente HTTP tipado hacia la API de FastAPI
│       └── context/         Estado global del pipeline comercial
├── docs/                    Diseño de sistemas, diccionario de datos y guías
├── docker-compose.yml       Orquestación de servicios en contenedores
└── AGENTS.md                Reglas de arquitectura y directrices de desarrollo
```
