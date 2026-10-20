# Cómo se descubren los negocios por rubro y ciudad

RepuSense necesita enumerar negocios por **rubro + ciudad** con rating y total de
reseñas para aplicar los filtros del brief (< 3.5 estrellas, > 10 reseñas).
La fuente de reseñas por negocio ya está resuelta
([fuente-de-resenas.md](fuente-de-resenas.md)); este documento define la fuente
de **discovery**.

## Veredicto

| Rol | Fuente | Estado |
| --- | --- | --- |
| Primaria | **SerpApi — Google Maps API** (`engine=google_maps`) | **Verificada (2026-10-17)**: 20/20 resultados con nombre, rating y reseñas |
| Fallback | **Google Places API (New) — Text Search** | Campos ya evaluados como útiles en fuente-de-resenas.md |
| Descartada | Vía anónima sin navegador (detalle abajo) | Invalidada con evidencia (7 pruebas) |

La primaria es de pago con capa gratuita (250 búsquedas/mes, 50/hora, sin
tarjeta) — el mismo Plan B que el equipo ya tenía documentado en
fuente-de-resenas.md, promovido a primaria para discovery.

## Plataformas consideradas

El entregable 1 del brief pide el listado de negocios afectados de **una**
plataforma. Google Maps sola cubre las dos capas del motor:

| Plataforma | Discovery | Reseñas | Estado |
| --- | --- | --- | --- |
| Google Maps | SerpApi (freemium, free tier) | Endpoint anónimo ([fuente-de-resenas.md](fuente-de-resenas.md)) | **Primaria — única del MVP** |
| Yelp | Business search oficial (posible; no se evaluó a fondo) | API de reseñas requiere plan pago (Enhanced/Premium) y entrega máx. 3 excerpt por negocio | Descartada: incluso pagando no entrega las 5 reseñas negativas del brief; dominada por Maps en ambas capas |
| TripAdvisor | Sin API pública | Sin API pública; scraping bloqueado por anti-bot agresivo (Cloudflare) | Descartada: inviable sin navegador. `systemDesign.md` aún la menciona en los pasos 4/5 — pendiente de reconciliar (tarea 13 del tablero) |

El modelo de datos mantiene la tabla `platform` preparada para
multiplataforma: incorporar otra fuente a futuro no exige cambios de esquema.

## Por qué la vía anónima no sirve para discovery

La fuente de reseñas funciona anónima porque `GetLocalBoqProxy` es un endpoint
de datos del frontend que no discrimina al cliente. El listado de búsqueda por
categoría NO comparte esa propiedad: Google solo lo sirve a un navegador real
(TLS + JS). Evidencia (2026-10-17, query "clínicas dentales en Bogotá"):

| # | Prueba | Resultado |
| --- | --- | --- |
| 1 | `search?tbm=map&api=1` con query de categoría | 200, 5.3 KB, **1 CID: el de la ciudad** (coordenadas del centroide); 0 ratings |
| 2 | `search?tbm=map` + `pb=!1s<q>!7i20!` (urllib, UA Chrome) | Mismo fallback de 5.3 KB, 1 CID |
| 3 | Ídem con curl `--http2` | Idéntico (5.3 KB) |
| 4 | Ídem con headers completos de navegador (Accept, Accept-Language, Sec-Fetch-*, sec-ch-ua) | Idéntico |
| 5 | Ídem + cookies reales del navegador (NID, `__Secure-STRP`; sin cookies de sesión) | Idéntico |
| 6 | El `pb` real que envía el navegador | Largo y con bindings de sesión (`!12m62!...`); no reproducible de forma estable |
| 7 | HTML de `/maps/search/<q>` anónimo | 200, 211 KB: **shell del SPA sin resultados** (0 CIDs, 0 reseñas) |

Además, en el navegador real el feed no pagina por JSON: los resultados por
categoría llegan inyectados en los **vector tiles binarios** del mapa
(`categorical-search-results-injection` en las URLs de tiles) — protobuf por
viewport, sin contrato razonable para reimplementar.

**Conclusión:** el discovery no tiene endpoint anónimo. Requiere API externa.

## Contrato de la fuente primaria (SerpApi Google Maps)

Endpoint (documentación: https://serpapi.com/google-maps-api):

```
GET https://serpapi.com/search?engine=google_maps&type=search&q=<rubro+ciudad>&hl=es-419&gl=mx&api_key=<key>
```

Parámetros relevantes:

| Parámetro | Valor | Nota |
| --- | --- | --- |
| `q` | `"<rubro> en <ciudad>"` | La ciudad va EN la query; con ciudad en la query no se recomienda `ll`/`nearby` (nota oficial de SerpApi) |
| `type` | `search` | Búsqueda por categoría (no `place` para un negocio concreto) |
| `start` | 0, 20, 40… | Paginación: 20 resultados por página; la respuesta trae `serpapi_pagination.next` listo para la siguiente |
| `hl` / `gl` | `es-419` / `mx` | Idioma/región de los resultados |

Campos por resultado en `local_results[]` (los que usa el lead):

| Campo SerpApi | Campo del lead |
| --- | --- |
| `title` | nombre |
| `rating` | calificación promedio |
| `reviews` | total de reseñas |
| `phone` | teléfono |
| `website` | sitio web |
| `address` | dirección |
| `place_id` (`ChIJ…`) | id externo (identity key) |
| `type` | categoría/rubro |
| `unclaimed_listing` | ficha sin dueño (señal de calidad del lead) |

Con estos campos los filtros del brief se aplican post-fetch, igual que lo
prevé el diseño (Paso 3 de `systemDesign.md`).

## Empalme con la fuente de reseñas (sin ingeniería nueva)

SerpApi no entrega las reseñas negativas más recientes (su API de reviews
consume plan aparte). No hace falta: el pipeline ya resuelve negocio → CID →
reseñas de forma anónima y gratuita.

```
SerpApi (discovery)                fuente-de-resenas.md (reseñas)
  title + ciudad  ──►  search?tbm=map&api=1  ──►  CID  ──►  GetLocalBoqProxy (sort=2)
                      (paso 1 ya validado)              5 reseñas negativas más recientes
```

El discovery alimenta al paso 1 existente con `"<title> <ciudad>"` como query.

## Costos y límites

- Plan gratuito: **250 búsquedas/mes, 50/hora, sin tarjeta**; solo descuenta
  búsquedas exitosas (documentado también en fuente-de-resenas.md).
- Rendimiento medido (2026-10-17): los filtros del brief (< 3.5 ★, > 10
  reseñas) califican a **1–5 de cada 20 resultados** según el rubro —
  dental: 0/80 en 4 páginas; taller mecánico: 1/20 en página 1; servicio
  técnico: 0/20. La ordenación por relevancia de Maps favorece a los bien
  puntuados: los leads viven en páginas profundas y en rubros con disputas
  de servicio recurrentes.
- Presupuesto de campaña: para ≥200 leads se necesitan del orden de
  **decenas a ~200 búsquedas** (matriz rubro×ciudad + paginación; Maps corta
  a ~120 resultados por query). El free tier mensual (250) cubre una campaña
  piloto; para cerrarla con margen en un mes, evaluar plan pago
  (https://serpapi.com/pricing).

## Fallback: Places API (New) Text Search

Si el equipo prefiere la vía oficial (ToS-compliant) o SerpApi cae:
`places:searchText` devuelve `rating`, `userRatingCount`, `businessStatus`,
`nationalPhoneNumber`, `websiteUri` — exactamente los campos que
fuente-de-resenas.md ya marcó como útiles de la API oficial. Requiere proyecto
GCP con facturación activa (tarjeta) y se cobra por consulta; por eso queda de
fallback y no de primaria en un MVP sin presupuesto.

## Señales de fallo

| Salida | Significado |
| --- | --- |
| HTTP 401 / `"error": "Invalid API key"` | clave inválida o vencida |
| `"local_results"` ausente o vacío | query sin resultados o cambio de esquema — revisar `q` primero |
| HTTP 429 | límite de 50/hora alcanzado — esperar y reintentar |
| Cuota agotada (`"error"` de plan) | 250/mes consumidos — activar fallback (Places) |

## Verificación

```bash
# Smoke test (requiere SERPAPI_KEY en el entorno): una búsqueda real debe
# devolver >= 20 resultados con nombre, rating y total de reseñas.
curl -s "https://serpapi.com/search?engine=google_maps&type=search&hl=es-419&gl=mx&q=cl%C3%ADnicas%20dentales%20en%20Bogot%C3%A1&api_key=$SERPAPI_KEY" \
  | python3 -c "import json,sys; r=json.load(sys.stdin)['local_results']; print(len(r), all('rating' in x and 'reviews' in x and x.get('title') for x in r[:20]))"
```

**Verificado (2026-10-17).** Ejecutado con la key del equipo (`SERPAPI_KEY`
en `backend/.env`, confirmado ignorado por git):

- «clínicas dentales en Bogotá» → **20/20 resultados** con nombre, rating y
  total de reseñas; `serpapi_pagination.next` presente.
- Cuenta: Free Plan, 250 búsquedas restantes en el mes.
- Rendimiento de filtros por rubro: ver «Costos y límites».
