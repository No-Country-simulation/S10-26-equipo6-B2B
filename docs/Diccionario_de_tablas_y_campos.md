# Diccionario de tablas y campos

## search: una ejecución de prospección

| **Campo**     | **Qué guarda**                                              | **Para qué sirve**                                                                               |
|---------------|-------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| search_id     | Identificador único (UUID) de la búsqueda                   | Distinguir cada ejecución y enlazarla con los negocios que encontró                              |
| sector        | El rubro, ej. “restaurantes”                                | Es lo que el vendedor escribe como input; define qué tipo de negocio buscar                      |
| city          | La ciudad, ej. “Medellín”                                   | Define dónde buscar                                                                              |
| max_rating    | Calificación máxima aceptada, ej. 3.5                       | Filtro “menos de 3.5 estrellas”: solo se guardan negocios por debajo de este valor               |
| min_reviews   | Mínimo de reseñas, ej. 10                                   | Filtro “más de 10 reseñas”: descarta negocios con muy pocas opiniones, cuya nota no es confiable |
| status        | Estado del trabajo: PENDING, IN_PROGRESS, COMPLETED, FAILED | El dashboard muestra si la búsqueda está en cola, corriendo, terminada o falló                   |
| created_at    | Cuándo el vendedor lanzó la búsqueda                        | Historial y orden de las búsquedas                                                               |
| started_at    | Cuándo el scraper empezó a trabajar                         | Medir cuánto tarda en cola                                                                       |
| finished_at   | Cuándo terminó (bien o mal)                                 | Con started_at, calcula la duración del scraping                                                 |
| error_message | Texto del error, solo si falló                              | Diagnosticar bloqueos anti-bot, timeouts, etc. Es nulo si todo salió bien                        |

## platform: catálogo de sitios de origen

| **Campo**   | **Qué guarda**                       | **Para qué sirve**                                   |
|-------------|--------------------------------------|------------------------------------------------------|
| platform_id | Número identificador (1, 2, 3…)      | Clave corta que usan otras tablas                    |
| name        | “Google Maps”, “TripAdvisor”, “Yelp” | Nombre legible; es único para que no haya duplicados |

## business: el lead

Representa al negocio como tal, sin importar en cuántas plataformas aparezca.

| **Campo**    | **Qué guarda**                    | **Para qué sirve**                                                     |
|--------------|-----------------------------------|------------------------------------------------------------------------|
| business_id  | Identificador único del lead      | Clave que une contactos, análisis y fichas                             |
| name         | Nombre del negocio                | Se muestra en el dashboard y se usa en el correo                       |
| sector       | Rubro del negocio                 | Filtrar y segmentar la prospección                                     |
| city         | Ciudad                            | Filtro del dashboard (“ciudad”)                                        |
| address      | Dirección física (opcional)       | Ayuda a confirmar que es el mismo local entre plataformas              |
| phone_number | Teléfono (opcional)               | Dato de contacto; suele ser genérico                                   |
| website      | Sitio web (opcional)              | Es el punto de partida para buscar el email del dueño                  |
| lead_status  | NEW, CONTACTED o DISCARDED        | Estado comercial: evita que dos vendedores contacten al mismo lead     |
| contacted_at | Fecha en que se contactó          | Obligatorio si el estado es CONTACTED; sirve para saber cuándo se hizo |
| created_at   | Cuándo se detectó por primera vez | Saber qué leads son nuevos                                             |
| updated_at   | Última modificación del registro  | Rastrear cambios                                                       |

## business_source: la ficha del negocio en una plataforma

| **Campo**          | **Qué guarda**                                                     | **Para qué sirve**                                                                            |
|--------------------|--------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| business_source_id | Identificador único de la ficha                                    | Clave para enlazar sus reseñas                                                                |
| business_id        | A qué lead pertenece                                               | Une la ficha con el negocio                                                                   |
| platform_id        | En qué plataforma está                                             | Indica si es de Google Maps, TripAdvisor, etc.                                                |
| external_id        | El ID que la plataforma le da al lugar (ej. el place_id de Google) | Junto con `platform_id` forma la **clave anti-duplicados** (UNIQUE): si la ficha vuelve a aparecer, se actualiza en vez de duplicarse |
| source_url         | Enlace a la ficha original                                         | Permite al vendedor abrir la página para verificar                                            |
| rating             | Calificación promedio, ej. 2.9                                     | Es el dato que se filtra y se muestra en la tabla                                             |
| total_reviews      | Cantidad total de reseñas                                          | Se usa para el filtro de “más de 10 reseñas”                                                  |
| last_scraped_at    | Cuándo se actualizaron estos datos                                 | Saber qué tan fresca es la información                                                        |

## search_business: qué búsqueda encontró qué negocio

| **Campo**   | **Qué guarda**                     | **Para qué sirve**                                           |
|-------------|------------------------------------|--------------------------------------------------------------|
| search_id   | La búsqueda                        | Junto con business_id forma la clave primaria                |
| business_id | El negocio encontrado              | Permite saber que un mismo negocio salió en varias búsquedas |
| found_at    | Cuándo se encontró en esa búsqueda | Trazabilidad de cada ejecución                               |

## review: reseñas extraídas

| **Campo**          | **Qué guarda**                               | **Para qué sirve**                                                  |
|--------------------|----------------------------------------------|---------------------------------------------------------------------|
| review_id          | Identificador único                          | Clave de la reseña                                                  |
| business_source_id | A qué ficha pertenece                        | Asocia la reseña a una plataforma concreta                          |
| external_id        | ID de la reseña en la plataforma (o un hash) | Único por ficha: junto con `business_source_id` evita guardar la misma reseña dos veces                             |
| author             | Nombre del autor (opcional)                  | Contexto; poco usado por el LLM                                     |
| rating             | Estrellas de 1 a 5                           | Distingue reseñas negativas (≤ 3) de positivas                      |
| content            | El texto del comentario (opcional)           | Es lo que lee el LLM para detectar el problema y redactar el correo |
| reviewed_at        | Fecha en que se escribió                     | Permite tomar las 5 más recientes                                   |
| scraped_at         | Cuándo la extrajo el scraper                 | Auditoría de la extracción                                          |

## problem_category: catálogo de problemas

| **Campo**           | **Qué guarda**                                         | **Para qué sirve**                                                              |
|---------------------|--------------------------------------------------------|---------------------------------------------------------------------------------|
| problem_category_id | Número identificador                                   | Clave corta                                                                     |
| name                | “Atención al cliente”, “Precios”, “Higiene”, “Demoras” | Lista controlada: el LLM elige de aquí y las etiquetas no quedan inconsistentes |

## ai_analysis: resultado del LLM

| **Campo**             | **Qué guarda**                         | **Para qué sirve**                                   |
|-----------------------|----------------------------------------|------------------------------------------------------|
| analysis_id           | Identificador único                    | Clave del análisis                                   |
| business_id           | El negocio analizado (único)           | Garantiza un solo análisis vigente por negocio       |
| problem_category_id   | El problema principal detectado        | Es el que se filtra y muestra en el dashboard        |
| pain_points_summary   | Resumen de las quejas (opcional)       | Contexto rápido para el vendedor                     |
| email_subject         | Asunto del correo en frío              | Listo para copiar                                    |
| email_first_paragraph | Primer párrafo basado en quejas reales | El diferenciador de IA del proyecto                  |
| ai_model              | Nombre del modelo usado (opcional)     | Saber con qué modelo se generó, por reproducibilidad |
| generated_at          | Cuándo se generó                       | Saber si el borrador está desactualizado             |

## contact: datos de contacto encontrados

| **Campo**    | **Qué guarda**                     | **Para qué sirve**                                                       |
|--------------|------------------------------------|--------------------------------------------------------------------------|
| contact_id   | Identificador único                | Clave del contacto                                                       |
| business_id  | A qué negocio pertenece            | Un negocio puede tener varios contactos                                  |
| contact_type | EMAIL o LINKEDIN                   | Distingue qué clase de dato es                                           |
| value        | El email o la URL del perfil       | El dato en sí. No se repite por negocio y los emails van en minúsculas   |
| source       | BUSINESS_WEBSITE o LINKEDIN_SEARCH | Cómo se obtuvo, para medir qué técnica de enriquecimiento funciona mejor |
| created_at   | Cuándo se encontró                 | Trazabilidad                                                             |
