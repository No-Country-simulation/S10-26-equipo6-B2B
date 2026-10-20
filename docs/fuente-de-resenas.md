# Cómo se obtienen las reseñas de Google

RepuSense obtiene las reseñas de Google con **dos `GET` anónimos** contra
`GetLocalBoqProxy`, el endpoint que consume el propio frontend de Google Maps.
Sin navegador, sin cookies, sin API key y sin costo.

La navegación headless no es viable: se probaron nueve combinaciones y todas
fueron bloqueadas por el lado del servidor.

## Ruta rápida

1. `search?tbm=map` con el nombre del negocio → devuelve el **CID**
2. `GetLocalBoqProxy` con el CID y `sort=2` → devuelve las **reseñas en JSON**
3. Filtrar `rating <= 3` con texto → quedar con las **5 más recientes**

Resultado medido: **100 reseñas únicas en 6.5 s, 0 duplicados, $0.**

## Uso

El contrato de arriba está implementado en `backend/app/etl/resenas.py`, que
solo usa la biblioteca estándar de Python. Corre desde `backend/` como módulo:

```bash
cd backend
python -m app.etl.resenas "Clínica Cotocollao Quito"
python -m app.etl.resenas "Bocanáriz Santiago" --sort 4
python -m app.etl.resenas "robstudiofit Talcahuano" --json
python -m app.etl.resenas --smoke-test
```

---

## Por qué no la API oficial de Places

Google documenta que el campo `reviews[]` devuelve opiniones **"ordenadas por
relevancia"** y que **"se puede devolver un máximo de 5"**. El brief pide las
5 reseñas **negativas más recientes**.

La API oficial no puede entregar ese resultado **ni siquiera con cuenta de
pago y facturación activada**.

| Requisito | API oficial | `GetLocalBoqProxy` |
| --- | --- | --- |
| 5 reseñas **negativas** | máximo 5 **en total**, sin filtro de estrellas | filtro libre |
| **Más recientes** | ordenadas por relevancia | `sort=2` |
| Cantidad total | 5 | paginado |
| Histograma de estrellas | no existe el campo | completo |

### Campos que sí sirven de la API oficial

| Campo | Utilidad |
| --- | --- |
| `rating` · `userRatingCount` | calificación y volumen del lead |
| `businessStatus` | `OPERATIONAL` · `CLOSED_TEMPORARILY` · `CLOSED_PERMANENTLY` · `FUTURE_OPENING` |
| `nationalPhoneNumber` · `websiteUri` | enriquecimiento de contacto |
| `reviewSummary` | **no sirve** — ver abajo |

### `reviewSummary` no sirve para nuestro segmento

Google genera un resumen con IA a partir de las reseñas, pero solo para
negocios bien evaluados. La documentación no menciona esta restricción; se
verificó empíricamente.

| Negocio | Rating | Reseñas | Resumen |
| --- | --- | --- | --- |
| Hospital San Rafael | 2.3 | 964 | ausente |
| Clínica Palermo | 2.5 | 1.450 | ausente |
| Hospital Británico BA | 3.3 | 3.644 | ausente |
| Bocanáriz | 4.6 | 5.747 | presente |
| Casa Gangotena | 4.7 | 701 | presente |

El volumen de reseñas se superpone entre ambos grupos — 536 a 3.649 contra 701
a 5.747 —, así que **el filtro no es por volumen sino por rating**. Nuestro
segmento es 1.5 a 3.5 estrellas, justo donde Google niega el resumen.

---

## Por qué no la navegación headless

El bloqueo lo pone Google, no la librería. Por eso Playwright, Scrapy y
Crawlee chocan contra el mismo portón.

| Método | Resultado |
| --- | --- |
| Places API — campo `reviews` | Demo Key elimina contenido de usuarios: devuelve `[]` |
| Places API — campo `reviewSummary` | ausente en 22 de 22 negocios con rating ≤ 3.4 |
| Puppeteer → Maps, headless vanilla | reseñas retenidas server-side: sin contador ni pestaña |
| Puppeteer → Maps, stealth headless | reseñas retenidas server-side |
| Puppeteer → Maps, stealth con ventana visible | reseñas retenidas server-side |
| Puppeteer → Search, vanilla | reCAPTCHA en el primer request |
| Puppeteer → Search, stealth headless | reCAPTCHA |
| Puppeteer → Search, stealth con ventana visible | reCAPTCHA |
| HTTP simple sin navegador | 200 OK con redirección `enablejs`: necesita JavaScript |

**Conclusión:** el navegador no es el problema ni la solución. Los tres caminos
probados eran los equivocados.

---

## Contrato del endpoint

Google retiró `listugcposts` a mediados de 2026, el endpoint que usaban casi
todos los proyectos de scraping. Su reemplazo —y lo que llama hoy el frontend
de Maps— es `GetLocalBoqProxy`.

### Paso 1 — obtener el CID

```
GET https://www.google.com/search?tbm=map&api=1&query=<buscar>
User-Agent: <user-agent de Chrome actual>
```

La respuesta contiene identificadores con la forma `0x…:0x…`. Filtro de
falsos positivos: **ambos lados deben tener 6 o más caracteres hexadecimales**
— `0x0:0x…` no es un CID válido.

### Paso 2 — obtener las reseñas

```
GET https://www.google.com/httpservice/web/PrivateLocalSearchUiDataService/
        GetLocalBoqProxy?msc=gwsrpc&reqpld=<json urlencoded>
User-Agent: <user-agent de Chrome actual>
Referer:    https://www.google.com/maps/
```

Ambas respuestas vienen con el prefijo anti-XSSI `)]}'` antes del JSON.

#### `reqpld` — primera página

```json
[null, [null, null, null, null, null, null, null, null, null,
        [null, <sort>, null, null, null, null, null, null, null,
         <pageSize>, null, ["<CID>"]]]]
```

#### `reqpld` — paginación

```json
[null, [null, null, null, null, null, null, null, null, null,
        [null, <sort>, null, null, null, null, null, null, null,
         null, null, ["<CID>"], null, null, null, null, null, null,
         null, "<token>"]]]]
```

> **Atención.** El token no va al mismo nivel que el CID: va un nivel más
> adentro, en la posición 19 del sub-array que arranca en el índice 9. Es el
> error más fácil de cometer al reimplementar.

#### Parámetros

| Parámetro | Valores |
| --- | --- |
| `sort` | `1` relevancia · `2` **más recientes** · `3` mayor · `4` menor |
| `pageSize` | máximo 60, por defecto 20 |

### Extracción de la respuesta

| Ruta | Contenido |
| --- | --- |
| `data[1][10][2]` | lista de reseñas |
| `data[1][10][6]` | token de la página siguiente |

#### Campos de cada reseña

| Índice | Contenido |
| --- | --- |
| `[1]` | estrellas |
| `[2][0]` | fecha legible, p. ej. `"una semana atrás"` |
| `[3][0]` | nombre del autor |
| `[5]` | review ID — sirve para deduplicar entre páginas |
| `[27]` / `[28]` / `[11]` | texto, en ese orden de preferencia |

#### Limpieza del texto

- `<br>` y `<br/>` → salto de línea
- Decodificar entidades HTML (`&amp;`, `&#39;`, …)

---

## Verificación

### Sobre negocios reales del segmento en crisis

| Caso | Esperado | Obtenido | Duplicados | Tiempo |
| --- | --- | --- | --- | --- |
| robstudiofit | 50 opiniones (según Google) | 50 reseñas únicas | 0 | 3.4 s |
| Clínica Cotocollao | — | 100 reseñas únicas | 0 | 6.5 s |
| Muestreo de 10 negocios | — | 9/10 con reseñas | — | ~1 s c/u |

Distribución de Cotocollao: `{1★: 61, 2★: 1, 3★: 5, 4★: 8, 5★: 25}` — que la
API oficial no puede entregar porque no tiene campo para el histograma.

### Validación cruzada

Con `sort=4` ("más baja") el endpoint devolvió como primera reseña exactamente
la misma que muestra el navegador de Google Maps con ese filtro seleccionado,
y en el mismo orden. Mismo origen, mismo resultado, sin navegador.

### Entregable del brief

Las 5 reseñas negativas más recientes de la Clínica Cotocollao, con texto
completo y orden cronológico estricto:

| # | Estrellas | Fecha | Autor |
| --- | --- | --- | --- |
| 1 | 1★ | una semana atrás | Camila meneses |
| 2 | 1★ | 4 semanas atrás | CRISTINA AGUILAR |
| 3 | 1★ | hace un mes | Mayra Arellano |
| 4 | 1★ | hace 3 meses | Jahiro Páez |
| 5 | 1★ | hace 4 meses | PAMELA GUADALUPE MONCAYO |

Las reseñas sin texto se descartan al filtrar, por lo que no consumen una de
las cinco plazas.

---

## Riesgos conocidos

| Riesgo | Mitigación |
| --- | --- |
| Endpoint interno, sin garantía de estabilidad — por eso murió `listugcposts` | Smoke test obligatorio que falle temprano si el payload deja de responder |
| Google puede cambiar el payload sin aviso | El acceso va detrás de una interfaz de proveedor, intercambiable con SerpApi |
| Bloqueo por tasa alta | Mantener ~1 req/s; 200 leads en minutos ya es suficiente |
| 1 de cada 10 búsquedas de CID devuelve 0 reseñas | Reintentar con los siguientes candidutos antes de rendirse |

### Plan B

**SerpApi** — plan gratuito de 250 búsquedas mensuales y 50 por hora. El alta
solo pide nombre, correo y contraseña: **no solicita tarjeta de crédito**, y
solo descuenta las búsquedas exitosas.

---

## Fuera de alcance

- **La persistencia de las reseñas.** El módulo devuelve las reseñas en
  memoria; cómo se guardan en la tabla `review` depende del esquema de tablas.
- **La estructura del pipeline de ingesta.** Se documentará junto con el
  esquema de tablas.

## Cómo verificar que sigue funcionando

```bash
cd backend && python -m app.etl.resenas --smoke-test
```

El chequeo corre contra un negocio conocido y valida los tres pasos:

1. El paso 1 debe devolver al menos un CID
2. El paso 2 debe devolver reseñas
3. La cantidad debe coincidir con la que muestra Google Maps

### Señales de fallo

| Salida | Significado |
| --- | --- |
| HTTP 400 | el formato del payload cambió — revisar el `reqpld` |
| HTTP 200 con lista vacía | el endpoint fue retirado |
| Estructura inesperada | la respuesta cambió de forma |

El script distingue los tres casos y los reporta con un mensaje accionable,
en lugar de fallar en silencio con un `IndexError`.
