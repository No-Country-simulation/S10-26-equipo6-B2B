<!--
================================================================================
CRITICAL DIRECTIVE FOR ALL AI AGENTS & LLMS (KIRO, CLAUDE, CURSOR, ANTIGRAVITY)
YOU MUST READ AND STRICTLY ADHERE TO THIS DOCUMENT BEFORE ANALYZING OR EDITING.
VIOLATION OF THESE RULES (ESPECIALLY HALLUCINATING CODE/LINES) IS NOT PERMITTED.
================================================================================
-->

# Directrices Obligatorias para Agentes de IA — RepuSense

Bienvenido al repositorio de **RepuSense**. Antes de emitir cualquier diagnóstico, auditoría, refactorización o propuesta de código, **DEBES CUMPLIR ESTAS 5 REGLAS INFRANQUEABLES**:

---

## 1. Protocolo Anti-Alucinación de Código (Ground Truth Obligatorio)
* **PROHIBIDO CITAR LÍNEAS O ARCHIVOS SIN LEERLOS:** Nunca cites números de línea o nombres de archivo de memoria. Debes usar herramientas (`grep`, lectura de archivos) para confirmar el contenido exacto y la línea actual.
* **EVIDENCIA TEXTUAL OBLIGATORIA:** Al señalar un bug, código duplicado o refutar un diagnóstico, debes mostrar el bloque de código literal extraído del archivo como prueba tangible.
* **PROHIBIDO INVENTAR BUGS O CÓDIGO DUPLICADO:** No asumas que existen validaciones duplicadas ni errores sintácticos sin verificar ambos extremos en el código real.
* **VERIFICACIÓN DE ENTORNO:** Antes de afirmar que falta una variable o configuración, inspecciona obligatoriamente `backend/.env.example`, `frontend/.env.example`, `pyproject.toml`, `package.json` y `docker-compose.yml`. (Ej: `REDIS_URL` ya está definido en `backend/.env.example`).
* **VERIFICACIÓN DE TESTS:** Antes de afirmar que un módulo o servicio tiene "0% de cobertura", ejecuta o revisa `pytest` y la suite en `backend/app/tests/`.

---

## 2. Arquitectura Oficial: Layered Monolith (Monolito por Capas Concéntricas)
* Este proyecto **NO** es una Arquitectura Hexagonal genérica ni utiliza CQRS. Está regido por la directriz oficial en `.agents/rules/backend-layered-architecture.md`:
  1. **Presentación (`backend/app/api/`):** FastAPI endpoints versionados (`v1/endpoints/`), `deps.py` y esquemas DTO Pydantic. No contiene SQL ni llamadas HTTP directas.
  2. **Servicios (`backend/app/services/`):** Casos de uso y orquestación (`ProspectingService`). No maneja HTTP. Inyecta dependencias por constructor.
  3. **Persistencia (`backend/app/models/` y `backend/app/repositories/`):** Modelos ORM (9 tablas en `entities.py`) y repositorios con operaciones UPSERT idempotentes.
  4. **Infraestructura (`backend/app/infrastructure/`):** Clientes externos (`serpapi_client`, `google_maps_client`) y sesión de base de datos (`session.py`).
* **Flujo Unidireccional Estricto:** `api` ➔ `services` ➔ `repositories` & `infrastructure`. Los modelos y repositorios nunca importan de capas superiores.
* **Prohibición de Sobreingeniería Prematura:** No propongas CQRS, microservicios ni capas innecesarias de protocolos para repositorios simples en esta fase de MVP.

---

## 3. Cero Carpetas Huérfanas y Sanitización
* No crees ni promuevas carpetas cascarón fuera de las 4 capas (`etl/`, `workers/`, `providers/`).
* Nota sobre `app/etl/resenas.py`: Es únicamente un wrapper de compatibilidad CLI hacia `infrastructure/external/google_maps_client.py`.

---

## 4. Tipado y Modelos Pydantic / SQLAlchemy
* **Modelos DTO:** Todos los schemas en `app/schemas/` son estrictos y fuertemente tipados (ej: `Negocio` y `SearchResponse` tienen tipos explícitos, no son dinámicos).
* **Nulabilidad en Respuestas:** Si un campo en `LeadResponse` tiene `= None`, es porque el lead en BD puede no haber sido enriquecido aún con web o teléfono. No es un error de omisión.
* **Diccionario de Datos:** Todo campo de entidad ORM está documentado en `docs/Diccionario_de_tablas_y_campos.md`.

---

## 5. Modo Consulta y Aprobación
* **NUNCA** modifiques código existente ni agregues dependencias sin presentar primero un diseño claro y recibir aprobación explícita del usuario.

