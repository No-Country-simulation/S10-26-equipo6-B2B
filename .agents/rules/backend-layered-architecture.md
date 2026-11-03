---
trigger: always_on
description: "Estándar de Arquitectura Monolítica por Capas y Sanitización para el Backend de RepuSense"
---

# Directriz Arquitectónica: Layered Monolith (Backend)

Al interactuar o modificar el código dentro de `backend/`:

1. **Estructura en 4 Capas Concéntricas:**
   - **Presentación (`app/api/`):** Controladores FastAPI versionados (`v1/endpoints/`), inyección de dependencias (`deps.py`) y esquemas Pydantic DTO. No contiene consultas SQL ni llamadas a APIs externas.
   - **Servicios (`app/services/`):** Orquestación de casos de uso y reglas de negocio (`ProspectingService`). No maneja dependencias HTTP directas.
   - **Persistencia (`app/models/` y `app/repositories/`):** Modelos ORM (9 tablas del ERD en `entities.py`) y acceso a base de datos mediante Repositorios (`search_repo`, `business_repo` con UPSERT anti-duplicados, `review_repo`).
   - **Infraestructura (`app/infrastructure/`):** Clientes HTTP externos limpios en `external/` (`serpapi_client`, `google_maps_client`), clientes de IA y sesiones de base de datos en `database/session.py`.

2. **Flujo Unidireccional de Dependencias:**
   - `api` llama a `services`.
   - `services` llama a `repositories` e `infrastructure`.
   - `models` y `repositories` nunca importan de `api` ni de `services`.

3. **Política de Sanitización y Cero Carpetas Huérfanas:**
   - No crear ni mantener carpetas cascarón vacías (como `workers/`, `etl/` o `providers/`).
   - Los tests unitarios deben importar directamente desde las capas concéntricas oficiales.

4. **Paginación Estandarizada:**
   - Los endpoints y métodos que devuelven listas deben implementar paginación mediante `PaginatedResponse[T]` con metadatos (`total`, `page`, `page_size`, `total_pages`, `has_next`).

5. **Modo Consulta y Validación:**
   - Nunca modificar código existente sin presentar primero el diseño y obtener aprobación explícita.
