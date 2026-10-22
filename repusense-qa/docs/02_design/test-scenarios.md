# RepuSense — Especificación de Escenarios de Prueba y Matriz de Cobertura (Fase 2)
> **Módulo:** Ingesta Asíncrona, Discovery, Extracción de Reseñas y Persistencia Relacional  
> **Trazabilidad:** Issues vinculados `#36`, `#38`, `#40`, `#43`  
> **Estándar:** ISTQB / Clean Test Architecture / Risk-Based Testing (RBT)

---

## 1. Alcance y Objetivos de Cobertura Técnica

El presente documento define los escenarios de prueba funcionales, de integración y no funcionales para el núcleo de prospección comercial de RepuSense. 

* **Objetivo de Negocio:** Blindar la detección de prospectos en crisis reputacional, garantizando que el equipo de ventas reciba únicamente leads calificados sin duplicados ni alucinaciones.
* **Fronteras del Sistema:**
  * Endpoint Discovery: `SerpApi Google Maps Engine` (Issue #40).
  * Endpoint Ingesta Reseñas: `GetLocalBoqProxy` (Issue #36).
  * Capa de Persistencia: `PostgreSQL 16` esquema de 9 tablas en Docker (Issue #38).
  * Worker Background: `Redis Queue` (Issue #43).

---

## 2. Análisis de Clases de Equivalencia y Valores Límite (BVA)

### 2.1. Filtro de Calificación Promedio (`rating`)
* **Regla de Negocio:** Negocios en crisis reputacional con calificación menor a 3.5 estrellas (`rating < 3.5`).
* **Clase Válida ($CE_1$):** Números reales en el intervalo $[1.0, 3.4]$.
* **Clase Inválida ($CE_2$):** Números reales en el intervalo $[3.5, 5.0]$.
* **Clase Inválida ($CE_3$):** Números fuera de rango ($< 1.0$, $> 5.0$), nulos o tipos de datos no numéricos.
* **Valores Límite (BVA):** `1.0` (Límite inferior), `3.4` (Límite superior válido), `3.5` (Límite superior rechazado), `3.6` (Valor externo).

### 2.2. Filtro de Volumen de Reseñas (`total_reviews`)
* **Regla de Negocio:** Negocios con representatividad estadística (`total_reviews > 10`).
* **Clase Válida ($CE_4$):** Números enteros en el intervalo $[11, \infty)$.
* **Clase Inválida ($CE_5$):** Números enteros en el intervalo $[0, 10]$.
* **Clase Inválida ($CE_6$):** Enteros negativos o valores nulos.
* **Valores Límite (BVA):** `9` (Rechazado), `10` (Frontera rechazada), `11` (Frontera aceptada).

### 2.3. Extracción de Reseñas Negativas (`extraer_negativas`)
* **Regla de Negocio:** Extraer hasta 5 reseñas negativas más recientes con texto (`rating <= 3` según normalización en `MAX_ESTRELLAS_NEGATIVAS`). Comentarios vacíos (`""`) deben descartarse sin consumir cupo de las 5 plazas.
* **Clase Válida ($CE_7$):** Reseñas con $1 \le \text{estrellas} \le 3$ y `longitud(texto) > 0`.
* **Clase Inválida ($CE_8$):** Reseñas con $\text{estrellas} > 3$.
* **Clase Inválida ($CE_9$):** Reseñas con texto nulo, vacío o compuesto únicamente por espacios en blanco.

---

## 3. Matriz de Ejecución y Casos de Prueba (Execution Test Matrix)

**Estados de Ejecución:**
* **`PASSED`:** La aserción técnica se cumplió al 100% contra el código o mock.
* **`FAILED`:** Discrepancia técnica detectada (hallazgo/bug que impacta la arquitectura o el negocio).
* **`BLOCKED`:** Caso diseñado que no puede ejecutarse por ausencia de dependencias externas (ej. migraciones no commiteadas).

### Módulo 1: Discovery y Filtrado Frontera (Issue #40 — `discovery.py`)

| ID Caso | Nombre del Caso de Prueba | Entrada (Payload Mock / Parámetros) | Resultado Esperado | Resultado Actual (Evidencia de Ejecución) | Estado | Severidad / Prioridad |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`TC-DISC-01`** | Frontera válida nominal de rating y volumen | `rating: 3.4`, `reviews: 11`, `place_id: "ChIJ_01"` | Cumple $3.4 < 3.5$ y $11 > 10$. Retorna 1 instancia normalizada de `Negocio`. | Acepta y normaliza `"Clínica Dental X"` correctamente como objeto `Negocio`. | **`PASSED`** | Crítica / P1-High |
| **`TC-DISC-02`** | Frontera exacta superior rechazada de rating (BVA Off-Point) | `rating: 3.5`, `reviews: 20`, `place_id: "ChIJ_02"` | Descarte estricto por no cumplir `rating < 3.5`. Retorna `[]`. | El negocio es descartado inmediatamente (`[]`). | **`PASSED`** | Crítica / P1-High |
| **`TC-DISC-03`** | Frontera exacta inferior rechazada de reseñas (BVA Off-Point) | `rating: 2.8`, `reviews: 10`, `place_id: "ChIJ_03"` | Descarte estricto por no cumplir `reviews > 10`. Retorna `[]`. | El negocio es descartado inmediatamente (`[]`). | **`PASSED`** | Grave / P1-High |
| **`TC-DISC-04`** | Paginación secuencial obligatoria con Pág. 1 vacía | Pág 1: 20 locales con 4.8★ + token `next`. Pág 2: 1 local con 2.9★ (25 reviews). | Avanza a `start=20` sin abortar y rescata el lead calificado de Pág. 2. | Consume `serpapi_pagination.next` y extrae el lead calificado de la segunda página. | **`PASSED`** | Crítica / P1-High |
| **`TC-DISC-05`** | Manejo de Cuota y Rate Limiting (HTTP 429) con Resiliencia | Mock de transporte inyectando cabecera `429 Too Many Requests`. | Captura la excepción, aplica reintento con backoff exponencial sin colapsar el pipeline. | `AssertionError`: El provider lanza `DiscoveryError(codigo=429)` de inmediato al primer intento (sin backoff ni reintento). | **`FAILED`** | Bloqueador / P1-High |
| **`TC-DISC-DUP`** | Deduplicación intra-búsqueda por `place_id` entre páginas | Mismo `place_id` (`ChIJ_dup_01`) retornado en corte de Pág 1 y Pág 2. | El método `buscar_negocios` deduplica en memoria y retorna 1 sola instancia. | `AssertionError`: Devolvió 2 instancias duplicadas en la lista acumulada de memoria (`len == 2`). | **`FAILED`** | Crítica / P1-High |

---

### Módulo 2: Extractor de Reseñas y Test Data Management (Issue #36 — `resenas.py`)

| ID Caso | Nombre del Caso de Prueba | Entrada (Payload Mock / Parámetros) | Resultado Esperado | Resultado Actual (Evidencia de Ejecución) | Estado | Severidad / Prioridad |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`TC-EXTR-01`** | Aislamiento y selección de 5 negativas con Golden Dataset | `dataset_critico_cotocollao.json` (8 reseñas mixtas: 1★, 2★, vacías y 5★). | Extrae exactamente las 5 reseñas más recientes $\le 3$★ con texto; descarta vacías y 5★. | Devuelve exactamente las 5 negativas con texto en orden cronológico (`r1, r4, r5, r6, r7`). | **`PASSED`** | Crítica / P1-High |
| **`TC-EXTR-02`** | Sanitización de entidades HTML y saltos de línea | `"Mala higiene &amp; suciedad<br>no lo recomiendo."` | Retorna string limpio con salto `\n` y entidades decodificadas. | Retorna `"Mala higiene & suciedad\nno lo recomiendo."`. | **`PASSED`** | Menor / P3-Low |
| **`TC-EXTR-03`** | Resiliencia ante estructura mutada en `GetLocalBoqProxy` | Payload sin sub-array de índice `[10]` (mutación de contrato Google). | Intercepta error de array y lanza `ErrorRecoleccion` estructurado sin crash. | Captura `IndexError/TypeError` y lanza `ErrorRecoleccion` con mensaje accionable. | **`PASSED`** | Bloqueador / P1-High |

---

### Módulo 3: Base de Datos, Idempotencia e IA (Issues #38, #43 — ERD 9 Tablas)

| ID Caso | Nombre del Caso de Prueba | Entrada (Payload Mock / Parámetros) | Resultado Esperado | Resultado Actual (Evidencia de Ejecución) | Estado | Severidad / Prioridad |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`TC-DB-01`** | Idempotencia por `external_id` y protección de `lead_status` | Re-escaneo de `external_id` existente con `lead_status = 'CONTACTED'` y nuevo rating. | `business_source` actualiza métricas (`UPSERT`); `business.lead_status` se mantiene intacto. | Bloqueado: `backend/migrations/` no contiene los scripts DDL de las 9 tablas SQL. | **`BLOCKED`** | Bloqueador / P1-High |
| **`TC-DB-02`** | Trazabilidad N:M en `search_business` ante redescubrimientos | Mismo `business_id` detectado en dos búsquedas distintas (`search_A` y `search_B`). | Inserta tupla `(search_B, business_id)` con nuevo `found_at` sin duplicar negocio padre. | Bloqueado: Pendiente esquema relacional del Issue #38. | **`BLOCKED`** | Grave / P2-Medium |
| **`TC-DB-03`** | Escudo Pydantic ante alucinaciones de categoría LLM | Inferencia del modelo con categoría fuera de catálogo (`"Mala_Atencion"`). | Reasigna determinísticamente a `"Otros"` (ID catalogado), evitando `SQL Error 23503`. | Bloqueado: Pendiente orquestador E2E y modelos relacionales del Issue #43. | **`BLOCKED`** | Crítica / P1-High |

---

## 4. Registro y Gestión de Defectos (Defect Log)

### Defecto `BUG-40-01`: Duplicación de Negocios por Frontera de Paginación
* **Severidad:** Crítica (Integridad de Datos) | **Prioridad:** P1-High
* **Módulo Afectado:** `backend/app/providers/discovery.py` (`SerpApiDiscovery.buscar_negocios`)
* **Caso Asociado:** `TC-DISC-DUP`
* **Causa Raíz:** `encontrados.extend(...)` concatena sin validar unicidad de `place_id`.
* **Blast Radius:** El extractor de quejas (`GetLocalBoqProxy`) procesará dos veces el mismo comercio, desperdiciando ancho de banda y arriesgando colisiones en la capa de persistencia.
* **Solución Técnica:** Agregar un conjunto en memoria `vistos = set()` para filtrar duplicados antes de retornar.

### Defecto `BUG-40-02`: Ausencia de Reintento / Backoff ante HTTP 429 en Provider
* **Severidad:** Grave (Resiliencia Operativa) | **Prioridad:** P1-High
* **Módulo Afectado:** `backend/app/providers/discovery.py`
* **Caso Asociado:** `TC-DISC-05`
* **Causa Raíz:** El método lanza `DiscoveryError(codigo=429)` en el primer fallo.
* **Blast Radius:** Si SerpApi responde 429 por superar las 50 req/h, la prospección aborta de inmediato en lugar de esperar la ventana de enfriamiento.
* **Solución Técnica:** Definir si el backoff exponencial se implementa dentro del adapter `SerpApiDiscovery` o si se delega formalmente al reintento de la cola en Redis (Worker del Issue #43).