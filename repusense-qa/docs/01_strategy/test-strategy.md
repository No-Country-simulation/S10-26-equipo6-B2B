# Estrategia de Pruebas de Calidad (Test Strategy)
**Equipo:** S10-26-equipo6-B2B  
**Proyecto:** RepuSense — Radar de Reputación en Crisis (NoCountry)  
**Dominio:** B2B SaaS / Marketing Digital & Automatización de Prospección  
**Versión:** 1.1  
**Responsables del área QA:**

* Maria Auxiliadora Vélez Mendoza

---

## 1. Contexto, Objetivos e Impacto de Negocio

### 1.1 El Problema de Negocio (Bottleneck)

La agencia de relaciones públicas y marketing digital especializada en recuperación de reputación local presenta un cuello de botella crítico en la adquisición de clientes:

* **Capacidad actual:** 3 vendedores dedican ~30 horas semanales a la búsqueda manual de prospectos en directorios (Google Maps, Yelp, TripAdvisor), generando un rendimiento marginal de solo 40 leads semanales.
* **Objetivo estratégico:** Escalar el volumen a cientos de leads calificados semanales mediante la automatización de la ingesta, análisis asistido por LLM y generación de borradores comerciales en frío.

### 1.2 Objetivos de la Estrategia de Calidad (Shift-Left QA)

1. **Garantizar la pureza del embudo comercial:** Validar que los criterios de calificación (`rating < 3.5` y `total_reviews > 10`) actúen como un filtro estricto sin escape de falsos positivos que degraden el tiempo del equipo de ventas.
2. **Proteger la integridad relacional y evitar la duplicidad:** Asegurar la idempotencia en la base de datos PostgreSQL mediante el uso estricto de claves únicas (`external_id`), evitando el envío redundante de correos y preservando la imagen corporativa de la agencia.
3. **Mitigar riesgos arquitectónicos perimetrales:** Evaluar la resiliencia del pipeline de extracción ante límites de cuota y bloqueos anti-bot, asegurando la consistencia del contrato de salida estructurado del modelo de lenguaje.

---

## 2. Alcance Técnico y Fronteras del Sistema (Scope & Boundaries)

Para mitigar el **Scope Creep** y blindar la entrega del **MVP** hacia el **Demo Day**, delimitamos las fronteras de calidad técnica en la siguiente matriz:

| Dimensión | Dentro del Alcance (In Scope) | Fuera del Alcance (Out of Scope) | Racional Técnico / Negocio |
| :--- | :--- | :--- | :--- |
| **Pipeline de Ingesta (Discovery + Extractor)** | • Ingesta de parámetros de entrada: `city` (Ciudad) y `sector` (Rubro).<br>• Filtros estrictos: `rating < 3.5` y `total_reviews > 10` vía SerpApi Google Maps.<br>• Extracción de hasta 5 reseñas negativas más recientes (`≤ 3 estrellas` con texto) vía `GetLocalBoqProxy`.<br>• Manejo de timeouts, paginación y códigos de límite de tasa (`HTTP 429`). | • Scraping multi-plataforma simultáneo (TripAdvisor / Yelp). Se prioriza Google Maps como fuente única del MVP.<br>• Navegación headless (Puppeteer / Playwright) para scraping, descartada por bloqueo server-side.<br>• Rotación de proxies residenciales de pago. | Enfocarse en el canal validado con mayor densidad de datos sin incurrir en bloqueos de navegador ni costos de infraestructura perimetral. |
| **Persistencia y Datos** | • Inserción idempotente en PostgreSQL 16 (Docker).<br>• Clave anti-duplicados por `external_id` (`place_id` / `CID`).<br>• Actualización de métricas (`rating`, `last_scraped_at`) sin sobreescribir `lead_status`.<br>• Población validada de ≥200 leads reales. | • Sharding de base de datos.<br>• Migraciones dinámicas complejas multi-tenant.<br>• Limpieza manual en caliente de datos productivos. | Proteger la integridad relacional y garantizar la muestra estadística requerida para el Demo Day. |
| **Capa de Inteligencia Artificial (LLM)** | • Categorización estricta del dolor contra catálogo cerrado `problem_category` (Atención, Precios, Higiene, Demoras, Otros).<br>• Generación de `email_subject` y `email_first_paragraph`.<br>• Validación de esquema de salida estructurada (JSON). | • Fine-tuning de modelos fundacionales.<br>• Agentes autónomos con memoria conversacional extendida.<br>• Reintentos infinitos ante fallos de cuota de API. | El valor radica en el *prompt engineering* determinístico y la validación de contratos, no en entrenar modelos. |
| **Dashboard & UI** | • Tabla de prospección con filtros (calificación, categoría, ciudad, estado).<br>• Acción: Copiar borrador de correo (*draft*).<br>• Acción: Exportación a CSV.<br>• Modificación de estado comercial (`lead_status = CONTACTED`). | • Envío automático masivo de correos (SendGrid/Mailgun).<br>• Sistema de autenticación de usuarios y roles (RBAC).<br>• Pasarela de pagos o facturación SaaS. | Eliminar fricción de configuración de servidores de correo y evitar riesgos de baneo de dominios en fase beta. |

---

## 3. Matriz de Riesgos Arquitectónicos y Mitigación (Shift-Left)

| Riesgo Arquitectónico | Impacto (H/M/L) | Probabilidad (H/M/L) | Estrategia de Mitigación (Shift-Left) |
| :--- | :---: | :---: | :--- |
| **Agotamiento de Cuota o Bloqueo por Tasa** <br>*(HTTP 429 en SerpApi / `GetLocalBoqProxy`)* | **H** | **H** | • Aislamiento de red en pruebas mediante *Golden Datasets* e inyección de transporte HTTP.<br>• Tasa de cortesía configurable (`~1 req/s` en reseñas y `2.0s` entre páginas de discovery).<br>• Validación de captura determinística de errores (`DiscoveryError` / `ErrorRecoleccion`) y *backoff* en el worker. |
| **Alucinaciones o JSON inválido del LLM** <br>*(Ruptura de contrato e integridad referencial)* | **H** | **M** | • Forzar respuestas mediante *Structured Outputs* nativos de la API del LLM.<br>• Validar el payload de salida en tiempo de ejecución utilizando esquemas estrictos de `Pydantic v2` con fallback automático a `"Otros"` (previniendo `SQL Error 23503 foreign_key_violation`).<br>• Diseñar pruebas unitarias con mocks de respuestas corruptas. |
| **Inconsistencia de Datos en Demo Day** <br>*(Duplicación de leads por reintentos)* | **M** | **M** | • Restricción de unicidad (`UNIQUE CONSTRAINT`) a nivel base de datos sobre `external_id` en `business_source`.<br>• Operaciones de inserción idempotentes (`ON CONFLICT DO UPDATE`) preservando `lead_status`. |
| **Flakiness en Pruebas E2E del Dashboard** <br>*(Falsos negativos al validar la tabla UI)* | **M** | **L** | • Implementar Page Object Model (POM) con selectores resilientes en `Playwright`.<br>• Utilizar *Auto-waiting* nativo antes de ejecutar aserciones sobre el DOM. |

---

## 4. Stack Técnico de Calidad Justificado

* **Lenguaje:** `Python 3.12+`. Mantiene paridad absoluta con la configuración del backend (`requires-python = ">=3.12"` en `backend/pyproject.toml`, `FastAPI` y `app/etl/resenas.py`), eliminando fricción de contexto técnico.
* **Test Runner:** `Pytest`. Modularidad mediante *fixtures* jerárquicos (`conftest.py`) y parametrización de casos límite (*Boundary Value Analysis - BVA*).
* **Validación de Esquemas:** `Pydantic v2`. Definición y auditoría de contratos estrictos para los modelos de discovery (`Negocio`), reseñas (`Resena`) y las respuestas estructuradas del LLM.
* **Aislamiento de Persistencia:** `PostgreSQL 16 + Redis 7 (Docker Compose)`. Entorno local reproducible e idéntico al de integración para certificar idempotencia y claves únicas.
* **UI Testing (Dashboard):** `Playwright (Python)`. Ejecución E2E determinística y *auto-waiting* nativo para validar el flujo comercial de filtrado, copiado de *draft* y actualización de estado en la Semana 4.

---

## 5. Quality Gates en CI/CD y Métricas de Calidad (DORA / KPIs)

### 5.1 Quality Gates por Pull Request
1. **Análisis Estático (Linter):** Ejecución limpia de `ruff check` en el backend y `pnpm lint` (`oxlint`) en el frontend con `0` errores.
2. **Pruebas Unitarias y de Contrato (Shift-Left):** Ejecución del 100% de la suite de `pytest` sobre *Golden Datasets* locales en `< 30 segundos`, sin consumir cuota de APIs externas.
3. **Verificación de Salud de Contratos Externos:** Smoke test controlado (`python -m app.etl.resenas --smoke-test`) para detectar cambios tempranos en la estructura de `GetLocalBoqProxy`.

### 5.2 KPIs y Criterios de Salida (Definition of Done hacia Demo Day)
* **Change Failure Rate (DORA):** `< 10%` en integraciones hacia la rama `main`.
* **Flakiness Index:** `0%` en la suite unitaria y de contratos gracias al aislamiento total de red mediante mocks e inyección de dependencias.
* **Pureza de Filtrado:** `100%` de cumplimiento estricto de las reglas del brief (`rating < 3.5` y `total_reviews > 10`) y selección de hasta 5 reseñas negativas (`≤ 3 estrellas` con texto).
* **Cero Duplicados:** `COUNT(*) = 1` por `external_id` tras ejecuciones repetidas sobre la misma combinación de rubro y ciudad.
