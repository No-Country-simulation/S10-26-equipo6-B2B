---
trigger: always_on
description: "Estándar de Arquitectura Monolítica por Capas para el Backend de RepuSense"
---

# Directriz Arquitectónica: Layered Monolith (Backend)

Al interactuar o modificar el código dentro de `backend/`:

1. **Estructura en 4 Capas Concéntricas:**
   - **Presentación (`app/api/`):** Controladores FastAPI, esquemas Pydantic (Request/Response) y validación. No contiene consultas SQL ni llamadas a APIs externas.
   - **Servicios (`app/services/`):** Orquestación de casos de uso y reglas de negocio. No maneja dependencias HTTP directas.
   - **Persistencia (`app/models/` y `app/repositories/`):** Modelos ORM (9 tablas del ERD) y acceso a base de datos mediante Repositorios.
   - **Infraestructura (`app/infrastructure/`):** Clientes HTTP externos (SerpApi, Google Maps RPC), clientes de IA y utilidades del sistema.

2. **Flujo Unidireccional de Dependencias:**
   - `api` llama a `services`.
   - `services` llama a `repositories` e `infrastructure`.
   - `models` y `repositories` nunca importan de `api` ni de `services`.

3. **Paginación Estandarizada:**
   - Los endpoints y métodos que devuelven listas deben implementar paginación mediante `PaginatedResponse[T]` con metadatos (`total`, `page`, `page_size`, `has_next`).

4. **Modo Consulta y Validación:**
   - Nunca modificar código existente sin presentar primero el diseño y obtener aprobación explícita.

