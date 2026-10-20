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

## Stack sugerido por el brief

| Capa | Opciones |
|------|----------|
| Data / Scraping | Python — BeautifulSoup, Selenium, Playwright, Scrapy · Node.js — Puppeteer, Crawlee |
| Backend | FastAPI (Python) · Express / NestJS (Node) |
| Frontend | React · Next.js · Vue |
| Base de datos | PostgreSQL · MongoDB |
| IA (opcional) | OpenAI API · Anthropic · modelos locales vía Ollama / LangChain |

> **Estado:** el stack todavía **no está cerrado** por el equipo.

---

## Estado del proyecto

### Construido

| | Artefacto | Dónde |
|---|---|---|
| ✅ | **Fuente de reseñas verificada** — contrato del endpoint anónimo, sin login ni cookies. Se probaron **9 combinaciones de scraping** que fueron bloqueadas (Maps y Search en headless, stealth, headed, y HTTP plano); las reseñas de la API oficial de Places quedan en `[]` o limitadas a 5 por relevancia, insuficiente para las 5 negativas más recientes que pide el brief. | [`docs/fuente-de-resenas.md`](docs/fuente-de-resenas.md) |
| ✅ | **Módulo ETL de reseñas** — obtiene reseñas de un negocio, con deduplicación por ID, rate limiting ~1 req/s, paginación, umbral de negativas `rating <= 3` y tres señales de fallo. | [`backend/app/etl/resenas.py`](backend/app/etl/resenas.py) |
| ✅ | **Infraestructura de contribución** — plantillas de issue y PR, guía de contribución. | [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) · [`.github/`](.github/) |

### Pendiente

| | Entregable | Estado |
|---|---|---|
| ⏳ | **1 · Motor de extracción funcional** | Fuente verificada y script de referencia listos. Falta el pipeline o API que reciba `rubro + ubicación`, aplique los filtros del brief y sirva los resultados. |
| ⬜ | **2 · Dashboard de prospección** | No iniciado. Tabla con filtros, export a CSV y copiar draft. |
| ⬜ | **3 · Base de datos con ≥ 200 leads** | No iniciado. Requiere el motor funcionando y el modelo de datos resuelto (desafío 3). |
| ⬜ | **4 · Feature diferenciador IA** | No iniciado. Asunto + primer párrafo generado desde las quejas reales. |
| ⬜ | **Enriquecimiento de contacto** | No iniciado. Email + LinkedIn del dueño (desafío 2). |
| ⬜ | **Cierre de stack** | Decisión pendiente del equipo. |

---

## Estructura del repositorio

```
├── .github/
│   ├── ISSUE_TEMPLATE/       Plantillas de bug y feature
│   └── pull_request_template.md
├── backend/
│   └── app/                  API FastAPI, capa ETL y proveedores externos
└── docs/
    ├── CONTRIBUTING.md       Guía de contribución y flujo de revisión
    └── fuente-de-resenas.md  Contrato del endpoint y evidencia de verificación
```

---

## Contribuir

Leé [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) antes de abrir un PR: convenciones de
commits, etiquetas de issue y el checklist de revisión.
