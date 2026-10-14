# RepuSense

Prospección automatizada para equipos comerciales que necesitan encontrar
empresas con **crisis de reputación**. Detecta negocios mal evaluados en
Google, analiza sus reseñas con IA y genera borradores de correo
personalizados.

## El problema

Un ejecutivo de ventas o un jefe de centro de atención dedica horas cada
semana a tres tareas manuales:

1. Recorrer el mapa de Google buscando negocios con calificaciones bajas.
2. Leer las reseñas para confirmar que el negocio **sigue operando**.
3. Releer esos mismos comentarios para redactar un correo genérico.

El resultado es prospección lenta, poca escala y mensajes que no conectan.

## El producto

| Paso | Qué hace |
| --- | --- |
| 1. Filtro | Ciudad y rubro → empresas con menos de 3.5 estrellas y más de 10 reseñas |
| 2. Evidencia | Las **5 reseñas negativas más recientes** de cada empresa |
| 3. Análisis | Causa raíz del problema, clasificada con IA |
| 4. Contacto | Borrador de correo personalizado para cada empresa |
| 5. Gestión | Dashboard con filtros y exportación a CSV |

Meta de la simulación: **200 empresas** procesadas.

## Cómo se obtienen los datos

Google Places API entrega los datos del negocio: calificación, cantidad de
reseñas, teléfono, sitio web y estado operativo. Para el **texto** de las
reseñas se consume un feed interno de Google Maps, con dos peticiones HTTP
anónimas: sin navegador, sin cookies y sin API key de pago.

Ambas rutas fueron verificadas sobre negocios reales del segmento:

| Verificación | Resultado |
| --- | --- |
| robstudiofit | 50 reseñas únicas — las mismas 50 que muestra Google |
| Clínica Cotocollao | 100 reseñas únicas en 6.5 s, 0 duplicados |
| Costo total | $0 — sin servicios de pago ni créditos |

La navegación headless **no es viable**: se probaron nueve combinaciones y
todas fueron bloqueadas por el lado del servidor. El detalle completo está en
[`docs/fuente-de-resenas.md`](docs/fuente-de-resenas.md).

## Estado del proyecto

### Construido

| Artefacto | Descripción |
| --- | --- |
| [`docs/fuente-de-resenas.md`](docs/fuente-de-resenas.md) | Contrato del endpoint, intentos fallidos, verificación y riesgos |
| [`scripts/obtener_resenas.py`](scripts/obtener_resenas.py) | Implementación de referencia de la fuente de reseñas |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Estándares del equipo: commits, ramas, issues y PRs |

### Pendiente

- [ ] Decisión de stack para backend y cola de tareas
- [ ] Esquema de base de datos
- [ ] Backend e ingesta de datos
- [ ] Integración con IA para el análisis de reseñas
- [ ] Dashboard y exportación

## Desarrollo

### Requisitos

Python 3.8 o superior. El script de referencia usa **solo la biblioteca
estándar**: no necesita `pip install`.

### Verificar que la fuente de datos responde

```bash
python scripts/obtener_resenas.py --smoke-test
```

### Recolectar reseñas de un negocio

```bash
python scripts/obtener_resenas.py "Clínica Cotocollao Quito"
python scripts/obtener_resenas.py "Bocanáriz Santiago" --sort 4
python scripts/obtener_resenas.py "robstudiofit Talcahuano" --json
```

### Contribuir

Leé [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md). En resumen: sin push
directo a `main`, Conventional Commits en español, y todo PR cierra un issue
aprobado con `Closes #ID`.

## Notas

- El presupuesto de la simulación es **$0**: sin servicios de pago ni
  tarjetas de crédito.
- El feed de reseñas es interno y no tiene garantía de estabilidad. El script
  incluye un smoke test y el documento describe las señales de fallo y el plan
  de respaldo.
