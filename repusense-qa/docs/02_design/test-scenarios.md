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
| **`TC-EXTR-04`** | Análisis de frontera (BVA) en filtro de reseñas negativas (`max_estrellas`) | Lote sintético con reseñas de 1★, 2★, 3★, 4★, 5★ bajo umbrales dinámicos (`max_estrellas=3` vs `2`). | Con umbral 3 incluye 1★, 2★ y 3★ descartando 4★ y 5★; con umbral 2 descarta 3★. | Validado determinísticamente con BVA sobre frontera superior del umbral configurable. | **`PASSED`** | Crítica / P1-High |
| **`TC-EXTR-05`** | Parsing y resiliencia de `fecha_absoluta` (Epoch ms a UTC datetime) | Epochs válidos (`1700000000000`), valores booleanos (`True`), corruptos (`"abc"`) y `None`. | Retorna `datetime` UTC para enteros válidos y `None` seguro ante fallas o tipos no soportados. | Retorna timestamp UTC exacto o `None` sin romper el pipeline ante mutaciones de Google. | **`PASSED`** | Grave / P2-Medium |
| **`TC-EXTR-06`** | Estampado de auditoría `scraped_at` por lote en `Resena` | Lote de reseñas procesado por `obtener_resenas` y validado contra esquema Pydantic `Resena`. | Todos los elementos del lote comparten idéntico `scraped_at` en UTC (una hora por lote). | Asignación en UTC verificada en contrato y modelo de datos. | **`PASSED`** | Grave / P2-Medium |

---

### Módulo 3: Base de Datos, Idempotencia y Migraciones (Issue #38, #78 — ERD 9 Tablas)

| ID Caso | Nombre del Caso de Prueba | Entrada (Payload Mock / Parámetros) | Resultado Esperado | Resultado Actual (Evidencia de Ejecución) | Estado | Severidad / Prioridad |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`TC-DB-01`** | Idempotencia por `external_id` y protección de `lead_status` | Re-escaneo de `external_id` existente con `lead_status = 'CONTACTED'` y nuevo rating. | `business_source` actualiza métricas (`UPSERT`); `business.lead_status` se mantiene intacto. | Validado en `test_layered_architecture.py::test_upsert_from_discovery_es_idempotente`. | **`PASSED`** | Bloqueador / P1-High |
| **`TC-DB-02`** | Creación y Restricciones de las 9 Tablas SQL | Ejecución de script DDL `backend/migrations/0001_init.sql` sobre motor relacional. | Crea tablas, claves foráneas, tipos UUID y restricciones únicas sin errores de sintaxis. | Validado en `test_migrations_sql.py::test_migracion_crea_todas_las_tablas`. | **`PASSED`** | Bloqueador / P1-High |

---

### Módulo 4: Endpoints de la API REST y Flujos Comerciales (Issue #25, #73, #76)

| ID Caso | Nombre del Caso de Prueba | Qué situación probamos | Lo que esperamos que haga el sistema | Estado | Prioridad |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **`TC-API-BUSQ-01`** | Iniciar búsqueda válida | El usuario escribe sector y ciudad correctos (ej: Restaurantes en Medellín). | Inicia la búsqueda de inmediato y entrega estado pendiente sin colapsar la pantalla. | ✅ **`PASSED`** | Crítica |
| **`TC-API-BUSQ-02`** | Rechazar calificación mayor a 5 estrellas | El usuario intenta enviar una calificación de 5.1 estrellas. | El sistema rechaza el valor y avisa amablemente que el límite máximo es 5 estrellas. | ✅ **`PASSED`** | Media |
| **`TC-API-BUSQ-03`** | Rechazar calificaciones negativas | El usuario intenta enviar un valor negativo (-0.5 estrellas). | El sistema no permite notas negativas y avisa el error. | ✅ **`PASSED`** | Media |
| **`TC-API-BUSQ-04`** | Rechazar mínimo de reseñas negativo | Se ingresa -1 en cantidad mínima de opiniones. | El sistema rechaza números negativos para las reseñas. | ✅ **`PASSED`** | Media |
| **`TC-API-BUSQ-05`** | Protegerse ante datos vacíos | Se intenta buscar dejando el sector o la ciudad en blanco. | El sistema avisa que son datos obligatorios y no realiza la búsqueda vacía. | ✅ **`PASSED`** | Alta |
| **`TC-API-SBUSQ-01`** | Consultar búsqueda inexistente | Se pide el estado de una búsqueda con un código que no existe en el sistema. | Responde claramente que la búsqueda no fue encontrada. | ✅ **`PASSED`** | Alta |
| **`TC-API-SBUSQ-02`** | Protegerse ante códigos inválidos | Se envía un texto con letras al azar en lugar del código de búsqueda. | El sistema detecta el formato incorrecto y avisa sin caerse. | ✅ **`PASSED`** | Media |
| **`TC-API-LEADS-01`** | Listar clientes con paginación | El vendedor pide ver los clientes encontrados divididos en páginas. | Entrega la lista ordenada, calculando bien el número de páginas y si hay más resultados. | ✅ **`PASSED`** | Crítica |
| **`TC-API-LEADS-02`** | Filtrar clientes por ciudad | El vendedor selecciona ver únicamente los clientes de una ciudad (ej. Quito). | La tabla solo muestra los clientes que pertenecen a esa ciudad. | ✅ **`PASSED`** | Alta |
| **`TC-API-LEADS-03`** | Evitar sobrecarga en la pantalla | El usuario intenta pedir más de 100 clientes de golpe (ej. 101). | El sistema no lo permite para cuidar el rendimiento y evitar que la pantalla se congele. | ✅ **`PASSED`** | Media |
| **`TC-API-PATCH-01`** | Marcar cliente como Contactado | El vendedor habla con el cliente y cambia su estado a 'Contactado'. | El sistema actualiza el estado a `CONTACTED` y registra la fecha de contacto. | ✅ **`PASSED`** | Crítica |
| **`TC-API-PATCH-02`** | Aceptar estado en minúsculas | El usuario escribe el estado en minúsculas (ej: 'discarded'). | El sistema lo entiende perfectamente y lo guarda normalizado en mayúsculas (`DISCARDED`). | ✅ **`PASSED`** | Media |
| **`TC-API-PATCH-03`** | Rechazar estados inventados | Se intenta poner un estado que no existe en el proceso comercial. | El sistema rechaza el texto y avisa cuáles son los únicos estados válidos permitidos. | ✅ **`PASSED`** | Alta |
| **`TC-API-AI-01`** | Consultar análisis de IA no generado | Se pide ver el correo de un cliente que todavía no ha sido analizado por la IA. | Responde de forma clara que el análisis de IA aún no ha sido generado. | ✅ **`PASSED`** | Alta |
| **`TC-API-AI-02`** | Generar correo en frío con IA | La IA lee las quejas del negocio y prepara el borrador para el vendedor. | Redacta el asunto, el primer párrafo personalizado y clasifica la queja en categorías reales. | ✅ **`PASSED`** | Crítica |
| **`TC-API-CONT-01`** | Listar contactos de un lead nuevo | Se consultan los medios de contacto de un cliente recién descubierto. | Entrega la lista vacía de forma segura mientras el scraper busca en la web. | ✅ **`PASSED`** | Media |
| **`TC-API-CONT-02`** | Cliente sin página web | Se intenta buscar correos de un negocio que no tiene sitio web registrado. | El buscador no revienta y responde con lista vacía de manera tranquila. | ✅ **`PASSED`** | Alta |

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