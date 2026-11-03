"""Cliente de reseñas de Google Maps: HTTP puro, sin navegador ni CLI.

Implementación de referencia del contrato documentado en
``docs/fuente-de-resenas.md``. Realiza dos peticiones HTTP anónimas contra el
endpoint que consume el propio frontend de Google Maps:

    1. ``search?tbm=map``   -> CID del lugar
    2. ``GetLocalBoqProxy`` -> reseñas en JSON

Este módulo no imprime en consola ni parsea argumentos: la capa de servicios
consume ``GoogleMapsClient`` y la CLI de compatibilidad vive en
``app.etl.resenas``.
"""

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime

from app.schemas.resenas import Resena

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Referer": "https://www.google.com/maps/",
}

URL_BUSQUEDA = "https://www.google.com/search?tbm=map&api=1&query="
URL_RESENAS = (
    "https://www.google.com/httpservice/web/PrivateLocalSearchUiDataService/"
    "GetLocalBoqProxy?msc=gwsrpc&reqpld="
)

# Tasa de cortesía: acelerar invita al bloqueo /sorry/.
PAUSA_ENTRE_PAGINAS = 0.6
PAUSA_ENTRE_CANDIDATOS = 0.3

# Códigos de orden que entiende el endpoint.
ORDENES = {
    1: "relevancia",
    2: "mas recientes",
    3: "mayor",
    4: "menor",
}


class ErrorRecoleccion(Exception):
    """Fallo recuperable durante la recolección, con mensaje accionable."""

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


def http_get(url, timeout=30):
    """Devuelve (cuerpo, código_http). Nunca lanza por HTTP no esperado."""
    peticion = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return respuesta.read().decode("utf-8", "replace"), respuesta.status
    except urllib.error.HTTPError as error:
        return error.read().decode("utf-8", "replace"), error.code
    except Exception as error:  # se reporta al caller como código 0
        return "EXC:" + str(error), 0


def parsear_cid(cuerpo):
    """Extrae los CID del cuerpo de la respuesta de búsqueda.

    El filtro exige 6 o más caracteres hexadecimales a cada lado para descartar
    los falsos positivos con la forma ``0x0:0x...``.
    """
    cuerpo = cuerpo.replace("\\u003a", ":")
    encontrados = []
    for coincidencia in re.finditer(r"0x([0-9a-fA-F]{6,}):0x([0-9a-fA-F]{6,})", cuerpo):
        cid = "0x" + coincidencia.group(1) + ":0x" + coincidencia.group(2)
        if cid not in encontrados:
            encontrados.append(cid)
    return encontrados


def obtener_cids(consulta):
    """Paso 1: busca el lugar y devuelve sus CID candidatos."""
    url = URL_BUSQUEDA + urllib.parse.quote(consulta)
    cuerpo, codigo = http_get(url)
    if codigo != 200:
        raise ErrorRecoleccion(
            f"la búsqueda devolvió HTTP {codigo}; probablemente hay un bloqueo por tasa",
            codigo,
        )
    return parsear_cid(cuerpo)


def construir_payload(cid, orden, tamano_pagina, token):
    """Arma el ``reqpld`` de GetLocalBoqProxy.

    En la primera página el sub-array del índice 9 lleva el tamaño de página.
    En la paginación ese mismo sub-array crece a 20 elementos y el token va en
    la posición 19, un nivel más adentro que el CID. Es el error más fácil de
    cometer al reimplementar el contrato.
    """
    if token is None:
        sub_arreglo = [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            [
                None,
                orden,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                tamano_pagina,
                None,
                [cid],
            ],
        ]
    else:
        sub_arreglo = [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            [
                None,
                orden,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [cid],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                token,
            ],
        ]
    return json.dumps([None, sub_arreglo], separators=(",", ":"))


def obtener_pagina(cid, orden, tamano_pagina, token=None):
    """Paso 2: pide una página de reseñas y devuelve (reseñas, token_siguiente)."""
    payload = construir_payload(cid, orden, tamano_pagina, token)
    url = URL_RESENAS + urllib.parse.quote(payload, safe="")
    cuerpo, codigo = http_get(url)

    if codigo == 400:
        raise ErrorRecoleccion(
            "HTTP 400 en GetLocalBoqProxy: el formato del payload cambió",
            codigo,
        )
    if codigo != 200:
        raise ErrorRecoleccion(f"GetLocalBoqProxy devolvió HTTP {codigo}", codigo)

    # El endpoint antepone el prefijo anti-XSSI ")]}'" al JSON.
    bruto = cuerpo[4:].lstrip("\n") if cuerpo.startswith(")]}'") else cuerpo
    try:
        datos = json.loads(bruto)
        resenas = datos[1][10][2]
        siguiente = datos[1][10][6]
    except (IndexError, TypeError, json.JSONDecodeError) as error:
        raise ErrorRecoleccion(
            f"la respuesta cambió de estructura ({error}): el endpoint fue modificado",
            codigo,
        ) from error

    if not resenas and token is None:
        raise ErrorRecoleccion(
            "HTTP 200 con la lista vacía: el endpoint fue retirado",
            codigo,
        )
    return resenas, siguiente


def limpiar_texto(valor):
    """Convierte los ``<br>`` en saltos de línea y decodifica entidades HTML."""
    if not isinstance(valor, str):
        return ""
    valor = re.sub(r"<br\s*/?>", "\n", valor, flags=re.I)
    return html.unescape(valor).strip()


def parsear_epoch_ms(valor):
    """Convierte el epoch en milisegundos del payload a ``datetime`` UTC.

    La fuente lo serializa como string de 13 dígitos en la posición 2 de la
    lista de fecha, un nivel más adentro que el texto relativo. Devuelve
    ``None`` cuando falta o no se puede leer: el payload de Google cambia sin
    aviso y una fecha ilegible no debe tumbar la recolección completa.
    """
    if not isinstance(valor, (str, int)) or isinstance(valor, bool):
        return None
    try:
        return datetime.fromtimestamp(int(valor) / 1000, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def extraer_campos(resena):
    """Mapea los índices posicionales del JSON a campos con nombre."""
    fecha_lista = resena[2] if len(resena) > 2 and isinstance(resena[2], list) else None
    autor_lista = resena[3] if len(resena) > 3 and isinstance(resena[3], list) else None
    epoch_ms = fecha_lista[2] if fecha_lista and len(fecha_lista) > 2 else None

    # El texto aparece en varios índices; se prefiere 27, luego 28 y luego 11.
    texto = ""
    for indice in (27, 28, 11):
        if indice < len(resena) and isinstance(resena[indice], str) and resena[indice].strip():
            texto = limpiar_texto(resena[indice])
            break

    return {
        "estrellas": resena[1] if len(resena) > 1 else None,
        "fecha": (fecha_lista or [None])[0] if fecha_lista else None,
        "fecha_absoluta": parsear_epoch_ms(epoch_ms),
        "autor": (autor_lista or [None])[0] if autor_lista else None,
        "id": resena[5] if len(resena) > 5 else "",
        "texto": texto,
    }


def _parsear_resenas(resenas):
    """Normaliza una lista cruda de reseñas con ``extraer_campos``."""
    return [extraer_campos(resena) for resena in resenas]


def obtener_resenas(
    consulta,
    orden=2,
    tamano_pagina=20,
    max_paginas=6,
    max_resenas=100,
    *,
    obtener_cids_fn: Callable | None = None,
    obtener_pagina_fn: Callable | None = None,
):
    """Recorre las páginas de un lugar, deduplicando por review ID.

    Devuelve (lista_de_reseñas, cid_utilizado). Las funciones de red son
    inyectables para que la capa de compatibilidad conserve la semántica de
    ``monkeypatch`` de los tests existentes.
    """
    buscar_cids = obtener_cids_fn or obtener_cids
    pedir_pagina = obtener_pagina_fn or obtener_pagina

    cids = buscar_cids(consulta)
    if not cids:
        raise ErrorRecoleccion("la búsqueda no devolvió ningún CID válido")

    for cid in cids[:4]:
        vistas, salida, token, pagina = set(), [], None, 0
        while pagina < max_paginas and len(salida) < max_resenas:
            resenas, token = pedir_pagina(cid, orden, tamano_pagina, token)
            nuevas = 0
            for resena in resenas:
                campos = extraer_campos(resena)
                if campos["id"] and campos["id"] in vistas:
                    continue
                if campos["id"]:
                    vistas.add(campos["id"])
                salida.append(campos)
                nuevas += 1
            pagina += 1
            if not token or nuevas == 0:
                break
            time.sleep(PAUSA_ENTRE_PAGINAS)

        if salida:
            # Una hora por lote: es la métrica que permite cronometrar la
            # recolección y reprogramar reintentos (ERD, systemDesign.md:281).
            momento = datetime.now(UTC)
            for campos in salida:
                campos["scraped_at"] = momento
            return salida, cid
        # CID válido pero sin reseñas: se prueba el siguiente candidato.
        time.sleep(PAUSA_ENTRE_CANDIDATOS)

    raise ErrorRecoleccion(f"ninguno de los {min(len(cids), 4)} CID candidatos devolvió reseñas")


def resumen_distribucion(resenas):
    """Histograma de estrellas, que la API oficial de Places no expone."""
    conteo = {}
    for resena in resenas:
        estrellas = resena["estrellas"]
        if estrellas is not None:
            conteo[estrellas] = conteo.get(estrellas, 0) + 1
    return dict(sorted(conteo.items(), reverse=True))


def extraer_negativas(resenas, cantidad, max_estrellas=3):
    """Las N reseñas negativas más recientes que tengan texto.

    Una reseña es negativa cuando su ``rating <= max_estrellas`` y su
    ``content`` no está vacío (RF2 de ``docs/systemDesign.md``). Las reseñas
    sin cuerpo se descartan para que no consuman una de las plazas.

    El umbral entra por parámetro para que el parsing siga siendo stdlib-only;
    quien lo lee de configuración es ``obtener_negativas``.
    """
    return [
        resena
        for resena in resenas
        if resena["estrellas"] is not None
        and resena["estrellas"] <= max_estrellas
        and resena["texto"]
    ][:cantidad]


def obtener_negativas(consulta, cantidad=5):
    """Las ``cantidad`` reseñas negativas más recientes de un negocio."""
    # Import diferido: el núcleo de parsing no debe arrastrar pydantic-settings.
    from app.core.config import settings

    resenas, _cid = obtener_resenas(consulta)
    return extraer_negativas(resenas, cantidad, settings.etl_negative_rating_max)


class GoogleMapsClient:
    """Adaptador de la fuente de reseñas para la capa de servicios."""

    def __init__(
        self,
        *,
        orden: int = 2,
        tamano_pagina: int = 20,
        max_paginas: int = 6,
        max_resenas: int = 100,
    ) -> None:
        self._orden = orden
        self._tamano_pagina = tamano_pagina
        self._max_paginas = max_paginas
        self._max_resenas = max_resenas

    def obtener_resenas(
        self,
        consulta: str,
        cantidad: int = 5,
    ) -> list[Resena]:
        """Devuelve las reseñas negativas más recientes ya validadas."""
        from app.core.config import settings

        resenas, _cid = obtener_resenas(
            consulta,
            orden=self._orden,
            tamano_pagina=self._tamano_pagina,
            max_paginas=self._max_paginas,
            max_resenas=self._max_resenas,
        )
        negativas = extraer_negativas(
            resenas,
            cantidad,
            settings.etl_negative_rating_max,
        )
        return [Resena(**campos) for campos in negativas]


# Alias de compatibilidad con la nomenclatura usada en el plan de arquitectura.
extraer_cid = parsear_cid
GoogleMapsError = ErrorRecoleccion
