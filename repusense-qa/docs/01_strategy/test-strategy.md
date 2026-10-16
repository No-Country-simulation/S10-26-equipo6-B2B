# Estrategia de Pruebas de Calidad (Test Strategy)
**Equipo:** S10-26-equipo6-B2B
**Proyecto:** RepuSense — Radar de Reputación en Crisis (NoCountry)
**Dominio:** B2B SaaS / Marketing Digital & Automatización de Prospección  
**Versión:** 1.0  
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

3. **Mitigar riesgos arquitectónicos perimetrales:** Evaluar la resiliencia del pipeline de scraping ante defensas anti-bot y asegurar la consistencia del contrato de salida estructurado del modelo de lenguaje.

---
## 2. Alcance Técnico y Fronteras del Sistema (Scope & Boundaries)

Para mitigar el **Scope Creep** y blindar la entrega del **MVP** hacia el **Demo Day**, delimitamos las fronteras de calidad técnica en la siguiente matriz:

| Dimensión | Dentro del Alcance (In Scope) | Fuera del Alcance (Out of Scope) | Racional Técnico / Negocio |
| :--- | :--- | :--- | :--- |
| **Pipeline de Ingesta (Scraper)** | • Ingesta de parámetros Entrada: city (Ciudad) y sector (Rubro) (`city`, `sector`).<br>• Filtros estrictos: `rating < 3.5` y `total_reviews > 10`.<br>• Extracción de hasta 5 reseñas negativas (≤ 2 estrellas con texto).<br>• Manejo de timeouts y códigos anti-bot (HTTP 429). | • Scraping multi-plataforma simultáneo (TripAdvisor / Yelp). Se prioriza Google Maps (`GetLocalBoqProxy`).<br>• Rotación de proxies residenciales de pago. | Enfocarse en el canal con mayor densidad de datos sin incurrir en costos de infraestructura perimetral. |
| **Persistencia y Datos** | • Inserción idempotente en PostgreSQL.<br>• Clave anti-duplicados por `external_id` (Place ID / CID).<br>• Actualización de métricas (`rating`, `last_scraped_at`) sin sobreescribir `lead_status`.<br>• Población validada de ≥200 leads reales. | • Sharding de base de datos.<br>• Migraciones dinámicas complejas multi-tenant.<br>• Limpieza manual en caliente de datos productivos. | Proteger la integridad relacional y garantizar la muestra estadística requerida para el Demo Day. |
| **Capa de Inteligencia Artificial (LLM)** | • Categorización estricta del dolor contra catálogo cerrado `problem_category` (Atención, Precios, Higiene, Demoras).<br>• Generación de `email_subject` y `email_first_paragraph`.<br>• Validación de esquema de salida estructurada (JSON). | • Fine-tuning de modelos fundacionales.<br>• Agentes autónomos con memoria conversacional extendida.<br>• Reintentos infinitos ante fallos de cuota de API. | El valor radica en el *prompt engineering* determinístico y la validación de contratos, no en entrenar modelos. |
| **Dashboard & UI** | • Tabla de prospección con filtros (calificación, categoría, ciudad, estado).<br>• Acción: Copiar borrador de correo (*draft*).<br>• Acción: Exportación a CSV.<br>• Modificación de estado comercial (`lead_status = CONTACTED`). | • Envío automático masivo de correos (SendGrid/Mailgun).<br>• Sistema de autenticación de usuarios y roles (RBAC).<br>• Pasarela de pagos o facturación SaaS. | Eliminar fricción de configuración de servidores de correo y evitar riesgos de baneo de dominios en fase beta. |
---

## 3. Matriz de Riesgos Arquitectónicos y Mitigación (Shift-Left)

| Riesgo Arquitectónico | Impacto (H/M/L) | Probabilidad (H/M/L) | Estrategia de Mitigación (Shift-Left) |
| :--- | :---: | :---: | :--- |
| **Bloqueo / Ban de IPs por Google Maps** <br>*(HTTP 429 / CAPTCHA)* | **H** | **H** | • Implementar un middleware de *Backoff* exponencial con *Jitter* aleatorio.<br>• Simular cabeceras de navegación reales mediante `Playwright`.<br>• Modular la tasa de peticiones (*rate-limiting*) en el pipeline de ingesta. |
| **Alucinaciones o JSON inválido del LLM** <br>*(Ruptura de contrato en el backend)* | **H** | **M** | • Forzar respuestas mediante *Structured Outputs* nativos de la API del LLM.<br>• Validar el payload de salida en tiempo de ejecución utilizando esquemas estrictos de `Pydantic v2`.<br>• Diseñar pruebas unitarias con mocks de respuestas corruptas. |
| **Inconsistencia de Datos en Demo Day** <br>*(Duplicación de leads por reintentos)* | **M** | **M** | • Restricción de unicidad (`UNIQUE CONSTRAINT`) a nivel base de datos sobre la clave compuesta (`Place ID` / `CID`).<br>• Operaciones de inserción idempotentes (`ON CONFLICT DO UPDATE`) mediante consultas SQL crudas o SQLAlchemy. |
| **Flakiness en Pruebas de la UI** <br>*(Falsos positivos al validar la tabla)* | **M** | **L** | • Migrar estrategias de selectores a la API nativa de localización de `Playwright` (vía texto y accesibilidad).<br>• Utilizar las capacidades de *Auto-waiting* del framework antes de ejecutar aserciones sobre el DOM. |

---

## 4. Stack Técnico de Calidad Justificado


| Dimensión | Dentro del Alcance (In Scope) | Fuera del Alcance (Out of Scope) | Racional Técnico / Negocio |
| :--- | :--- | :--- | :--- |
| **Pipeline de Ingesta (Scraper)** | • Ingesta de parámetros (`city`, `sector`).<br>• Filtros estrictos: `rating < 3.5` y `total_reviews > 10`.<br>• Extracción de hasta 5 reseñas negativas (≤2 estrellas con texto).<br>• Manejo de timeouts y códigos anti-bot (HTTP 429). | • Scraping multi-plataforma simultáneo (TripAdvisor / Yelp). Se prioriza Google Maps (`GetLocalBoqProxy`).<br>• Rotación de proxies residenciales de pago. | Enfocarse en el canal con mayor densidad de datos sin incurrir en costos de infraestructura perimetral. |
| **Persistencia y Datos** | • Inserción idempotente en PostgreSQL.<br>• Clave anti-duplicados por `external_id` (Place ID / CID).<br>• Actualización de métricas (`rating`, `last_scraped_at`) sin sobreescribir `lead_status`.<br>• Población validada de ≥200 leads reales. | • Sharding de base de datos.<br>• Migraciones dinámicas complejas multi-tenant.<br>• Limpieza manual en caliente de datos productivos. | Proteger la integridad relacional y garantizar la muestra estadística requerida para el Demo Day. |
| **Capa de Inteligencia Artificial (LLM)** | • Categorización estricta del dolor contra catálogo cerrado `problem_category` (Atención, Precios, Higiene, Demoras).<br>• Generación de `email_subject` y `email_first_paragraph`.<br>• Validación de esquema de salida estructurada (JSON). | • Fine-tuning de modelos fundacionales.<br>• Agentes autónomos con memoria conversacional extendida.<br>• Reintentos infinitos ante fallos de cuota de API. | El valor radica en el *prompt engineering* determinístico y la validación de contratos, no en entrenar modelos. |
| **Dashboard & UI** | • Tabla de prospección con filtros (calificación, categoría, ciudad, estado).<br>• Acción: Copiar borrador de correo (*draft*).<br>• Acción: Exportación a CSV.<br>• Modificación de estado comercial (`lead_status = CONTACTED`). | • Envío automático masivo de correos (SendGrid/Mailgun).<br>• Sistema de autenticación de usuarios y roles (RBAC).<br>• Pasarela de pagos o facturación SaaS. | Eliminar fricción de configuración de servidores de correo y evitar riesgos de baneo de dominios en fase beta. |


## 5. Stack Técnico de Calidad Justificado

* **Lenguaje:** `Python 3.11+`. Mantiene paridad absoluta con el script validado `obtener_resenas.py` y el backend (`FastAPI`), reduciendo la fricción de contexto técnico.
* **Test Runner:** `Pytest`. Modularidad mediante *fixtures* jerárquicos (alcance de función y sesión) y parametrización de casos límite (*Boundary Value Analysis - BVA*).
* **Validación de Esquemas:** `Pydantic v2`. Definición de contratos estrictos para los payloads de la API y las respuestas estructuradas del LLM.
* **Aislamiento de Persistencia:** `Testcontainers (PostgreSQL)`. Despliegue de instancias efímeras en Docker para asegurar idempotencia total y aislamiento en pruebas de integración de base de datos.
* **UI Testing (Dashboard):** `Playwright (Python)`. Mayor velocidad de ejecución y *auto-waiting* nativo frente a Selenium, reduciendo el *Flakiness Index* en la tabla de leads y el copiado del *draft*.

