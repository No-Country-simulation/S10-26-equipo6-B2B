# RepuSense — Diseño de Sistema (Framework de 6 Pasos)

Diseño del sistema RepuSense estructurado según el framework de 6 pasos de diseño de sistemas. El modelo de datos definitivo corresponde al ERD del equipo (fuente: `Captura_de_pantalla_de_2026-10-15_18-04-42.png`).

Índice:
1. Aclarar Requisitos y Alcance
2. Estimaciones Rápidas (Back-of-the-Envelope)
3. Definición de APIs y Modelo de Datos
4. Diseño de Alto Nivel (HLD)
5. Profundización (Deep Dives)
6. Cuellos de Botella, Escalado y Resiliencia

---

## Paso 1 — Aclarar Requisitos y Alcance

El brief del proyecto cubre ~80-90% de la información de negocio. Este paso la traduce en especificaciones formales: Requisitos Funcionales, Exclusiones (Fuera de Alcance) y Requisitos No Funcionales (Escala, Latencia y Restricciones).

### 1. Requisitos Funcionales (lo que el sistema DEBE hacer)

- **RF1. Parámetros de búsqueda dinámicos:** permitir al usuario iniciar una prospección especificando Ciudad, Rubro (ej. "clínicas dentales") y filtros (calificación < 3.5 estrellas y > 10 reseñas).
- **RF2. Extracción automática (scraping):** recopilar nombre del negocio, rating, total de reseñas, teléfono, sitio web y el texto de las últimas 5 reseñas negativas.
- **RF3. Enriquecimiento secundario de contactos:** navegar el sitio web del negocio para rastrear un correo electrónico de contacto o enlace relevante.
- **RF4. Análisis e inteligencia con IA (LLM):** enviar las reseñas al modelo de IA para clasificar la causa principal del descontento (atención, precios, higiene, demoras) y redactar un borrador de correo personalizado (asunto + primer párrafo).
- **RF5. Dashboard de gestión:** ofrecer una interfaz tipo tabla con filtros por calificación y problema, visualización de contactos, copia de borradores y exportación a CSV.

### 2. Fuera de Alcance (exclusiones del MVP)

Para evitar la sobreingeniería y asegurar el cumplimiento de la entrega del proyecto:

- **Envío automático de correos (email dispatching):** el sistema no envía e-mails masivos directamente; únicamente genera el borrador personalizado para que el vendedor lo copie o exporte.
- **Scraping síncrono en tiempo real en la petición HTTP:** el scraping no se ejecuta bloqueando la pantalla del navegador; la tarea se procesa en segundo plano.
- **Gestión de CRM completo:** no se construirá una plataforma compleja de seguimiento de ventas multipartes.

### 3. Requisitos No Funcionales (cualidades del sistema y escala)

- **RNF1. Escala y almacenamiento inicial:** la base de datos debe ser capaz de procesar y almacenar al menos 200 a 500 leads reales para las pruebas del MVP.
- **RNF2. Arquitectura asíncrona y latencia:** el dashboard debe responder consultas de lectura en menos de 200 ms, mientras que las tareas pesadas de extracción e IA se ejecutan en segundo plano mediante colas de trabajo.
- **RNF3. Deduplicación e idempotencia:** identificar comercios mediante una clave única (place_id o URL de origen) para actualizar datos existentes en lugar de duplicar registros al repetir búsquedas.
- **RNF4. Resiliencia anti-bot económica:** diseñar estrategias de scraping (User-Agents rotativos, retardos aleatorios) para evitar bloqueos tempranos sin depender de proxies premium.

## Paso 2 — Estimaciones Rápidas (Back-of-the-Envelope)

Objetivo: traducir los requisitos del MVP a números concretos (tráfico, peticiones web, consumo de tokens de IA y almacenamiento) para tomar decisiones informadas de infraestructura antes de diseñar la base de datos o la API.

### 1. Volumen de trabajo y QPS

- Uso estimado del MVP: 10 búsquedas/prospecciones por día ejecutadas por el equipo comercial.
- Leads procesados por búsqueda: 50 negocios escaneados para filtrar los ~20 con peor calificación.
- Negocios procesados al día: 10 búsquedas × 50 negocios = 500 negocios/día.
- QPS síncrono (lecturas en el dashboard): un puñado de usuarios consultando la interfaz genera < 1 QPS.
- **Conclusión de carga:** el sistema no es de alto tráfico síncrono, sino intensivo en procesamiento por lotes en segundo plano (batch / async heavy).

### 2. Estimación de scraping y peticiones HTTP

Por cada negocio analizado se ejecutan aproximadamente 5 peticiones HTTP:

1. Petición a los resultados de la búsqueda.
2. Petición al detalle del negocio.
3. Petición para extraer la sección de las últimas 5 reseñas negativas.
4. 1 a 2 peticiones a la web propia del comercio (para rastrear correos o contactos).

- Total de peticiones HTTP diarias: 500 negocios × 5 peticiones = 2.500 peticiones/día.
- Tiempo de ejecución recomendado: si un worker procesa cada negocio en 10 segundos (para simular comportamiento humano y evitar bloqueos de IP), procesar 500 negocios tomará 500 × 10 s = 5.000 segundos ≈ 1,4 horas de trabajo continuo al día.

### 3. Consumo de tokens y costos de IA (LLM)

Suponiendo que de los 500 negocios diarios, 200 cumplen los criterios y pasan al análisis del LLM:

- Prompt de entrada (input): instrucciones de clasificación + 5 reseñas negativas (~150 palabras c/u) + datos básicos ≈ 1.000 tokens/negocio.
  - Total diario: 200 × 1.000 = 200.000 tokens/día (≈ 6 millones de tokens/mes).
- Respuesta del modelo (output): categoría + puntos de dolor + borrador de correo ≈ 250 tokens/negocio.
  - Total diario: 200 × 250 = 50.000 tokens/día (≈ 1,5 millones de tokens/mes).
- Costo mensual estimado (modelo eficiente tipo GPT-4o-mini o equivalente):
  - Input: 6M × $0,15/M = $0,90 USD.
  - Output: 1,5M × $0,60/M = $0,90 USD.
  - **Costo total de IA: ≈ $2 a $5 USD/mes** (viable y de bajo costo para el MVP).

### 4. Estimación de almacenamiento en base de datos

Peso promedio de un lead completo guardado:

- Registro del negocio (negocios): ~1 KB.
- Reseñas extraídas (reseñas): 5 reseñas × ~500 bytes = ~2,5 KB.
- Análisis de IA y borrador (analisis_ia): ~1,5 KB.
- **Peso total por lead: ~5 KB.**

Proyección de almacenamiento:

- 1.000 leads guardados en el MVP: 1.000 × 5 KB = 5 MB.
- 100.000 leads acumulados en un año: 100.000 × 5 KB = 500 MB ≈ 0,5 GB.
- **Conclusión de infraestructura:** cualquier base de datos PostgreSQL estándar (incluso en capa gratuita de proveedores cloud como Render, Supabase o Neon) manejará este volumen durante años sin problemas de espacio o índices.

**Conclusión del paso:** no se necesita un clúster masivo ni almacenamiento distribuido especial, sino un pipeline asíncrono simple y robusto.

## Paso 3 — Definición de APIs y Modelo de Datos

### 1. Contrato de API (RESTful)

Dado que las tareas de extracción e IA son lentas, la API es asíncrona para evitar bloqueos y timeouts en el navegador.

#### A. Iniciar prospección (crear búsqueda) — `POST /api/v1/busquedas`

Cuerpo de la petición (JSON):

```json
{
  "termino": "clínicas dentales",
  "ciudad": "Bogotá",
  "filtro_estrellas_max": 3.5,
  "min_reseñas": 10
}
```

Respuesta (202 Accepted):

```json
{
  "busqueda_id": "8f3a1d2e-4b5c-6a7b-8c9d-0e1f2a3b4c5d",
  "estado": "PENDING",
  "mensaje": "Prospección iniciada en segundo plano"
}
```

#### B. Consultar estado de la búsqueda — `GET /api/v1/busquedas/{id}`

Respuesta (200 OK):

```json
{
  "busqueda_id": "8f3a1d2e-4b5c-6a7b-8c9d-0e1f2a3b4c5d",
  "estado": "COMPLETED",
  "progreso": "100%",
  "leads_procesados": 20
}
```

#### C. Listar leads filtrados (dashboard comercial) — `GET /api/v1/leads`

Parámetros de consulta (query params): `?busqueda_id=uuid&categoria_problema=atencion&page=1&limit=20`

Respuesta (200 OK):

```json
{
  "total": 20,
  "pagina": 1,
  "datos": [
    {
      "id": "11223344-5566-7788-9900-aabbccddeeff",
      "nombre": "Clínica Dental Ejemplo",
      "calificacion": 3.1,
      "telefono": "+573001234567",
      "email": "contacto@dentalejemplo.com",
      "problema_principal": "Atención al cliente",
      "borrador_asunto": "Mejora la retención de pacientes en Clínica Dental Ejemplo",
      "estado_lead": "ANALIZADO_IA"
    }
  ]
}
```

### 2. Esquema relacional inicial — versión simplificada (4 tablas)

> Propuesta inicial de referencia; el ERD de 9 tablas (sección 3) la supera y es el modelo validado.

A. Tabla busquedas:

```sql
CREATE TABLE busquedas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    termino VARCHAR(100) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    filtro_estrellas_max DECIMAL(2,1) DEFAULT 3.5,
    estado VARCHAR(20) CHECK (estado IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

B. Tabla negocios (control de idempotencia con UNIQUE):

```sql
CREATE TABLE negocios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    busqueda_id UUID REFERENCES busquedas(id) ON DELETE SET NULL,
    place_id VARCHAR(255) UNIQUE NOT NULL, -- Identificador único de la plataforma (evita duplicados)
    nombre VARCHAR(150) NOT NULL,
    plataforma VARCHAR(50) NOT NULL,
    calificacion_promedio DECIMAL(2,1),
    total_reseñas INT,
    sitio_web VARCHAR(255),
    telefono VARCHAR(50),
    email VARCHAR(150),
    estado_lead VARCHAR(30) DEFAULT 'NUEVO',
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para acelerar filtros en el Dashboard
CREATE INDEX idx_negocios_busqueda_rating ON negocios(busqueda_id, calificacion_promedio);
```

C. Tabla reseñas:

```sql
CREATE TABLE reseñas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    negocio_id UUID REFERENCES negocios(id) ON DELETE CASCADE,
    autor VARCHAR(100),
    calificacion INT CHECK (calificacion BETWEEN 1 AND 5),
    texto TEXT NOT NULL,
    fecha_reseña TIMESTAMP WITH TIME ZONE
);
```

D. Tabla analisis_ia:

```sql
CREATE TABLE analisis_ia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    negocio_id UUID UNIQUE REFERENCES negocios(id) ON DELETE CASCADE,
    categoria_problema VARCHAR(100) NOT NULL, -- ej. Atención, Precios, Tiempos
    resumen_puntos_dolor TEXT NOT NULL,
    asunto_email VARCHAR(200) NOT NULL,
    cuerpo_email_borrador TEXT NOT NULL,
    generado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

Mecanismo de deduplicación (UPSERT): al repetir una búsqueda en la misma zona, la base de datos utiliza la cláusula ON CONFLICT sobre la restricción de unicidad place_id:

```sql
INSERT INTO negocios (place_id, nombre, plataforma, calificacion_promedio, sitio_web, telefono)
VALUES ('ChIJN1t_tDeuEmsRUsoyG83frY4', 'Clínica Dental Ejemplo', 'Google Maps', 3.1, 'dentalejemplo.com', '+573001234567')
ON CONFLICT (place_id)
DO UPDATE SET
    calificacion_promedio = EXCLUDED.calificacion_promedio,
    actualizado_en = CURRENT_TIMESTAMP;
```

### 3. Modelo de datos validado — ERD del equipo (9 tablas)

Fuente: `Captura_de_pantalla_de_2026-10-15_18-04-42.png`. Esquema normalizado y escalable; supera la versión simplificada anterior, resolviendo idempotencia, soporte multiplataforma y auditoría del procesamiento asíncrono.

El modelo define 9 tablas organizadas con claves primarias (uuid / smallint), claves foráneas y restricciones de unicidad (UK):

**1. Gestión de búsquedas y rastreo: search y search_business**

- `search`: almacena los parámetros de la prospección (sector, city, max_rating, min_reviews), su estado (status) y métricas temporales de ejecución (started_at, finished_at, error_message).
- `search_business` (tabla intermedia N:M): desacopla las búsquedas de los negocios (search_id, business_id, found_at). Si un negocio es encontrado en múltiples prospecciones distintas (ej. "odontología" y "clínicas dentales"), no se duplica la entidad en la base de datos, conservando el historial completo de hallazgos.

**2. Entidad central del comercio y contactos multi-canal: business y contact**

- `business`: almacena la entidad física o comercial (name, sector, city, address, phone_number, website, lead_status, contacted_at, created_at, last_update).
- `contact`: tabla 1:N vinculada a business. Permite registrar múltiples vías de contacto (contact_type: email, teléfono, formulario web; value, source), ideal para almacenar varios correos encontrados durante el enriquecimiento secundario.

**3. Abstracción multiplataforma de fichas y reseñas: platform, business_source y review**

- `platform`: catálogo maestro de fuentes de origen (platform_id, name: Google Maps, TripAdvisor, Yelp, etc.).
- `business_source`: representa la ficha específica de un negocio en una plataforma concreta (external_id, source_url, rating, total_reviews, last_scraped_at). Permite que un mismo negocio tenga métricas e identidades separadas en Google y TripAdvisor.
- `review`: guarda las reseñas individuales extraídas de cada ficha (business_source_id, external_id, author, rating, content, reviewed_at, scraped_at).

**4. Inteligencia artificial y clasificación: problem_category y ai_analysis**

- `problem_category`: catálogo maestro para estandarizar los tipos de problemas identificados por la IA (problem_category_id, name).
- `ai_analysis`: almacena el resultado de la inferencia del modelo (business_id, problem_category_id, pain_points_summary, email_subject, email_first_paragraph, ai_model, generated_at). Incluye el modelo de IA utilizado (ai_model), garantizando trazabilidad al cambiar de proveedor o versión del LLM.

**Fortalezas principales del esquema:**

- **Idempotencia y sin duplicados:** el desacoplamiento entre search, business y business_source garantiza que re-escanear una misma ciudad actualice la ficha (business_source) o añada nuevas reseñas (review) sin duplicar la empresa principal.
- **Escalabilidad multiplataforma:** añadir Yelp o Trustpilot basta con insertar un registro en platform, sin modificar la estructura ni romper la tabla business.
- **Auditoría del procesamiento asíncrono:** los campos started_at, finished_at, error_message en search y scraped_at en review permiten monitorear fallos en el worker de scraping y reprogramar reintentos con precisión.

## Paso 4 — Diseño de Alto Nivel (HLD)

### 1. Diagrama de arquitectura

```
[ Cliente / Frontend ]
   (React / Next.js)
          │
          │  1. POST /api/v1/busquedas
          ▼
 [ API Backend / Gateway ] ◄──────────► [ Base de Datos Relacional ]
   (FastAPI / Node.js)                   (PostgreSQL - 9 Tablas)
          │                                       ▲
          │  2. Encola trabajo                    │
          ▼                                       │ 5. Guarda resultados
  [ Cola de Tareas ]                              │    en schema relacional
 (Redis + Celery/BullMQ)                          │    (search, business,
          │                                       │     business_source,
          │  3. Consume tarea                     │     review, contact,
          ▼                                       │     ai_analysis)
 [ Worker: Scraper Engine ] ──────────────────────┤
 (Puppeteer / Playwright)                         │
          │                                       │
          │  4. Envía reseñas                     │
          ▼                                       │
  [ Servicio de IA / LLM ] ───────────────────────┘
  (API OpenAI / Ollama)
```

### 2. Componentes principales y persistencia

**Capa de entrada (API Gateway / Backend):**

- Recibe la solicitud de prospección e inserta un nuevo registro en la tabla search con estado PENDING.
- Retorna una respuesta asíncrona inmediata 202 Accepted con el ID de la búsqueda y coloca el identificador en la cola de tareas en memoria (Redis).

**Orquestación asíncrona (cola de tareas & worker):**

- El worker toma la tarea de Redis y actualiza el estado de la búsqueda en search a IN_PROGRESS registrando la hora de inicio (started_at).
- Si ocurre un error fatal durante la ejecución, el worker captura la excepción y actualiza search.status a FAILED detallando la causa en error_message.

**Capa de extracción (scraper engine & enriquecimiento):**

- Ejecuta la navegación headless en plataformas de mapas/reseñas (Google Maps, TripAdvisor) según las plataformas registradas en la tabla platform.
- Inserta o actualiza la entidad del comercio en business y su ficha específica en business_source (guardando rating, total_reviews y last_scraped_at).
- Vincula la búsqueda con el negocio en la tabla intermedia search_business.
- Almacena las reseñas negativas asociadas a la ficha en review y registra múltiples canales de contacto detectados (emails, teléfonos) en contact.

**Capa de inteligencia artificial (servicio LLM):**

- El worker toma el conjunto de reseñas negativas guardadas en review y las envía al LLM.
- La respuesta formateada asigna una categoría estandarizada de la tabla problem_category e inserta los resultados en ai_analysis (pain_points_summary, email_subject, email_first_paragraph y el modelo utilizado ai_model).

**Cierre del trabajo:**

- Al finalizar el procesamiento de todos los negocios hallados, el worker actualiza el registro en search cambiando su estado a COMPLETED y marcando la marca de tiempo en finished_at.

### 3. Flujo de datos de extremo a extremo (end-to-end)

1. **Petición del usuario:** el vendedor solicita buscar "clínicas dentales" en "Bogotá" con calificación < 3.5 estrellas.
2. **Creación de registro:** la API crea la entrada en search y delega a Redis.
3. **Scraping e identificación de fichas:** el worker obtiene los comercios, verifica mediante business_source.external_id si el negocio ya existía y actualiza sus métricas.
4. **Captura de reseñas y contacto:** extrae las 5 reseñas negativas más recientes hacia review y raspa la web oficial del comercio para guardar correos en contact.
5. **Generación con IA:** el LLM determina el problema principal (ej. "Atención al cliente"), vincula el problem_category_id y guarda el borrador del correo en ai_analysis.
6. **Visualización en dashboard:** el frontend consulta GET /api/v1/leads ejecutando una consulta JOIN entre business, contact, problem_category y ai_analysis para mostrar la tabla de prospectos listos para contactar.

## Paso 5 — Profundización (Deep Dives)

Los tres componentes técnicamente más exigentes y críticos para garantizar que el sistema funcione sin fallos ni bloqueos en producción.

### 1. Estrategia anti-bot y navegación resiliente (scraper engine)

Para evitar que las plataformas de mapas y reseñas bloqueen las direcciones IP o detecten la automatización sin recurrir a proxies premium costosos:

- **Evasión de huella digital (stealth browser):** uso de Puppeteer Stealth o Playwright enmascarando las propiedades típicas de automatización (ocultando navigator.webdriver, simulando WebGL y encabezados navigator.plugins).
- **Rotación dinámica de User-Agents y headers:** variación sistemática del encabezado User-Agent utilizando firmas actualizadas de navegadores reales (Chrome, Firefox, Safari) en Windows y macOS.
- **Simulación de comportamiento humano:**
  - Delays o pausas aleatorias entre peticiones (entre 1,5 y 4,5 segundos).
  - Desplazamiento (scroll) progresivo para activar la carga perezosa (lazy loading) de reseñas.
- **Manejo de respuestas de bloqueo:**
  - Detección automática de códigos 429 Too Many Requests o 403 Forbidden.
  - Captura de la excepción sin detener el servidor y reprogramación de la tarea en la cola de Redis aplicando tiempo de espera exponencial (exponential backoff).

### 2. Pipeline de enriquecimiento en cascada para datos de contacto

Las plataformas de reseñas no suelen mostrar el correo directo de las empresas, por lo que se implementa un flujo en cascada:

```
[ Ficha de Origen ] ──► ¿Tiene email público? ──YES──► Guarda en tabla 'contact'
         │
        NO
         ▼
[ Extrae URL Sitio Web ] ──► Navega a la web del negocio
                                  │
                                  ├─► Revisa /contacto, /nosotros, footer
                                  └─► Aplica Regex de Emails
                                            │
                                            ▼
                                Guarda en tabla 'contact'
```

- **Paso A:** si la plataforma no proporciona email, el worker extrae el campo website de la ficha del negocio.
- **Paso B:** se ejecuta un scraping secundario sobre el sitio web oficial explorando las rutas /contacto, /nosotros y el pie de página (footer).
- **Paso C:** filtrado de correos mediante expresiones regulares (regex) y registro del resultado en la tabla contact, vinculándolo a la entidad business.

### 3. Inferencia estructurada con el LLM (JSON Mode)

Para evitar errores de sintaxis al guardar las respuestas de la IA en la base de datos, se fuerza al modelo de lenguaje (API de OpenAI o modelo local vía Ollama) a responder con garantía de formato JSON estricto.

Estructura del contrato de salida (output schema):

```json
{
  "problem_category_id": 2,
  "categoria_nombre": "Atención al cliente",
  "pain_points_summary": "Se identificaron quejas recurrentes sobre demoras en recepción y mala actitud del personal.",
  "email_subject": "Propuesta para optimizar la atención a pacientes en [Nombre Negocio]",
  "email_first_paragraph": "Hola, analizamos recientemente las experiencias de sus clientes y notamos oportunidades clave en la gestión de citas..."
}
```

Integración con la base de datos: los campos generados se mapean directamente a las columnas de la tabla ai_analysis (pain_points_summary, email_subject, email_first_paragraph, ai_model) y se vinculan a la categoría correspondiente en problem_category.

## Paso 6 — Cuellos de Botella, Escalado y Resiliencia

Identificación de las posibles fallas bajo carga y definición de los mecanismos de protección.

### 1. Identificación de cuellos de botella y puntos únicos de fallo (SPOF)

**Bloqueo masivo de IPs durante el scraping:**

- Riesgo: si una plataforma como Google Maps o TripAdvisor detecta múltiples peticiones automatizadas desde la misma dirección IP, bloqueará temporal o permanentemente el acceso.
- Mitigación: patrón Circuit Breaker (disyuntor). Si la tasa de respuestas con código 429 o 403 supera un umbral determinado, el sistema pausa automáticamente la cola de scraping durante un tiempo, registra el evento en el campo error_message de la tabla search y aplica un reintento con tiempo de espera exponencial (exponential backoff con jitter).

**Límites de tasa (rate limits) en la API del LLM:**

- Riesgo: generar borradores de correo para cientos de leads simultáneamente puede superar la cuota de tokens por minuto (RPM/TPM) del proveedor de IA.
- Mitigación: desacoplamiento mediante colas independientes en Redis (scraping_queue vs. ai_queue). Un worker procesa las llamadas a la IA con una frecuencia controlada. Si la API de IA falla, los mensajes se mueven a una Dead Letter Queue (DLQ) para ser reprocesados sin perder los datos ya raspados en review y contact.

**Acumulación de trabajos y tiempos de cuelgue (timeouts):**

- Riesgo: un proceso de scraping puede quedar colgado indefinidamente navegando un sitio web mal optimizado.
- Mitigación: tiempos límite estrictos (timeouts) por tarea (máximo 30 segundos por negocio). Si un sitio web no responde, el worker omite el enriquecimiento de ese lead específico, guarda el registro en business con lo obtenido hasta el momento y continúa con el siguiente.

### 2. Estrategia de escalado futuro (scale out)

- **Escalado horizontal de workers:** dado que los workers son stateless, es posible aumentar el número de contenedores de scraping en función de la longitud de la cola de Redis.
- **Réplicas de lectura en PostgreSQL:** para asegurar que las lecturas del dashboard comercial (GET /api/v1/leads) sean instantáneas (< 200 ms), se pueden derivar las consultas de lectura a réplicas de lectura de PostgreSQL, manteniendo la base de datos primaria dedicada exclusivamente a las escrituras de los workers.

## Resumen ejecutivo del diseño

RepuSense es un pipeline asíncrono y resiliente de prospección comercial:

1. **Entrada:** la API (POST /api/v1/busquedas) registra la solicitud en la tabla search y delega la tarea pesada a Redis.
2. **Procesamiento:** un worker de Puppeteer/Playwright extrae los comercios, evita duplicados mediante business_source.external_id, captura las reseñas negativas en review y busca correos electrónicos en la web del negocio para almacenarlos en contact.
3. **Inteligencia:** un LLM en modo JSON estricto clasifica la causa del descontento en problem_category y genera el borrador del correo en ai_analysis.
4. **Resiliencia:** manejo de fallos con Circuit Breakers, colas desacopladas en Redis y actualización transparente de estados para el usuario en el dashboard comercial.
