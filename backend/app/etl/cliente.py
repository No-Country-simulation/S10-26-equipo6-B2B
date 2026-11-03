"""Cliente HTTP y protocolo del endpoint interno de Google Maps.

Implementa el transporte HTTP y la serialización del payload ``reqpld``
para interactuar con ``GetLocalBoqProxy`` y la búsqueda por mapa.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

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

PAUSA_ENTRE_PAGINAS = 0.6
PAUSA_ENTRE_CANDIDATOS = 0.3

ORDENES = {
    1: "relevancia",
    2: "mas recientes",
    3: "mayor",
    4: "menor",
}


class ErrorRecoleccion(Exception):
    """Fallo recuperable durante la recoleccion, con mensaje accionable."""

    def __init__(self, mensaje: str, codigo: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo = codigo


def http_get(url: str, timeout: int = 30) -> tuple[str, int]:
    """Devuelve (cuerpo, codigo_http). Nunca lanza por HTTP no esperado."""
    peticion = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return respuesta.read().decode("utf-8", "replace"), respuesta.status
    except urllib.error.HTTPError as error:
        return error.read().decode("utf-8", "replace"), error.code
    except Exception as error:
        return f"EXC:{error}", 0


def parsear_cid(cuerpo: str) -> list[str]:
    """Extrae los CID del cuerpo de la respuesta de busqueda.

    El filtro exige 6 o mas caracteres hexadecimales a cada lado para descartar
    los falsos positivos con la forma ``0x0:0x...``.
    """
    cuerpo = cuerpo.replace("\\u003a", ":")
    encontrados: list[str] = []
    for coincidencia in re.finditer(r"0x([0-9a-fA-F]{6,}):0x([0-9a-fA-F]{6,})", cuerpo):
        cid = "0x" + coincidencia.group(1) + ":0x" + coincidencia.group(2)
        if cid not in encontrados:
            encontrados.append(cid)
    return encontrados


def obtener_cids(consulta: str) -> list[str]:
    """Paso 1: busca el lugar y devuelve sus CID candidatos."""
    url = URL_BUSQUEDA + urllib.parse.quote(consulta)
    cuerpo, codigo = http_get(url)
    if codigo != 200:
        raise ErrorRecoleccion(
            f"la busqueda devolvio HTTP {codigo}; probablemente hay un bloqueo por tasa",
            codigo,
        )
    return parsear_cid(cuerpo)


def construir_payload(cid: str, orden: int, tamano_pagina: int, token: str | None) -> str:
    """Arma el ``reqpld`` de GetLocalBoqProxy.

    En la primera pagina el sub-array del índice 9 lleva el tamaño de página.
    En la paginación ese mismo sub-array crece a 20 elementos y el token va en
    la posición 19, un nivel más adentro que el CID.
    """
    if token is None:
        sub_arreglo: list[Any] = [
            None, None, None, None, None, None, None, None, None,
            [
                None, orden, None, None, None, None, None, None, None,
                tamano_pagina, None, [cid],
            ],
        ]
    else:
        sub_arreglo = [
            None, None, None, None, None, None, None, None, None,
            [
                None, orden, None, None, None, None, None, None, None,
                None, None, [cid], None, None, None, None, None, None,
                None, token,
            ],
        ]
    return json.dumps([None, sub_arreglo], separators=(",", ":"))


def obtener_pagina(
    cid: str, orden: int, tamano_pagina: int, token: str | None = None
) -> tuple[list[Any], str | None]:
    """Paso 2: pide una página de reseñas y devuelve (reseñas, token_siguiente)."""
    payload = construir_payload(cid, orden, tamano_pagina, token)
    url = URL_RESENAS + urllib.parse.quote(payload, safe="")
    cuerpo, codigo = http_get(url)

    if codigo == 400:
        raise ErrorRecoleccion(
            "HTTP 400 en GetLocalBoqProxy: el formato del payload cambio",
            codigo,
        )
    if codigo != 200:
        raise ErrorRecoleccion(
            f"GetLocalBoqProxy devolvio HTTP {codigo}", codigo
        )

    # El endpoint antepone el prefijo anti-XSSI ")]}'" al JSON.
    bruto = cuerpo[4:].lstrip("\n") if cuerpo.startswith(")]}'") else cuerpo
    try:
        datos = json.loads(bruto)
        reseñas = datos[1][10][2]
        siguiente = datos[1][10][6]
    except (IndexError, TypeError, json.JSONDecodeError) as error:
        raise ErrorRecoleccion(
            f"la respuesta cambio de estructura ({error}): el endpoint fue modificado",
            codigo,
        ) from error

    if not reseñas and token is None:
        raise ErrorRecoleccion(
            "HTTP 200 con la lista vacia: el endpoint fue retirado",
            codigo,
        )
    return reseñas, siguiente
