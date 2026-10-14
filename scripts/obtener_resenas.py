"""Recolecta reseñas de Google Maps sin navegador.

Implementación de referencia del contrato documentado en
`docs/fuente-de-resenas.md`. Realiza dos peticiones HTTP anónimas contra el
endpoint que consume el propio frontend de Google Maps:

    1. ``search?tbm=map``   -> CID del lugar
    2. ``GetLocalBoqProxy`` -> reseñas en JSON

Solo usa la biblioteca estandar de Python: sin dependencias externas, sin
navegador, sin cookies y sin API key.

Uso:
    python scripts/obtener_resenas.py "Clínica Cotocollao Quito"
    python scripts/obtener_resenas.py "Bocanáriz Santiago" --sort 4
    python scripts/obtener_resenas.py "robstudiofit Talcahuano" --json
    python scripts/obtener_resenas.py --smoke-test

Advertencia:
    El endpoint es interno y no tiene garantia de estabilidad: Google retiro
    ``listugcposts`` a mediados de 2026 y proyectos con miles de estrellas
    quedaron con errores 403. Ejecutar ``--smoke-test`` antes de confiar en el
    endpoint en cualquier momento futuro.
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Las consolas de Windows usan cp1252 por defecto y arruinan los acentos.
sys.stdout.reconfigure(encoding="utf-8")

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

# Tasa de cortesia: acelerar invita al bloqueo /sorry/.
PAUSA_ENTRE_PAGINAS = 0.6
PAUSA_ENTRE_CANDIDATOS = 0.3

# Codigos de orden que entiende el endpoint.
ORDENES = {
    1: "relevancia",
    2: "mas recientes",
    3: "mayor",
    4: "menor",
}


class ErrorRecoleccion(Exception):
    """Fallo recuperable durante la recoleccion, con mensaje accionable."""

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


def http_get(url, timeout=30):
    """Devuelve (cuerpo, codigo_http). Nunca lanza por HTTP no esperado."""
    peticion = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return respuesta.read().decode("utf-8", "replace"), respuesta.status
    except urllib.error.HTTPError as error:
        return error.read().decode("utf-8", "replace"), error.code
    except Exception as error:  # noqa: BLE001 - se reporta al caller como codigo 0
        return "EXC:" + str(error), 0


def parsear_cid(cuerpo):
    """Extrae los CID del cuerpo de la respuesta de busqueda.

    El filtro exige 6 o mas caracteres hexadecimales a cada lado para descartar
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
            "la busqueda devolvio HTTP %s; probablemente hay un bloqueo por tasa" % codigo,
            codigo,
        )
    return parsear_cid(cuerpo)


def construir_payload(cid, orden, tamano_pagina, token):
    """Arma el ``reqpld`` de GetLocalBoqProxy.

    En la primera pagina el sub-array del índice 9 lleva el tamaño de página.
    En la paginación ese mismo sub-array crece a 20 elementos y el token va en
    la posición 19, un nivel más adentro que el CID. Es el error más fácil de
    cometer al reimplementar el contrato.
    """
    if token is None:
        sub_arreglo = [
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


def obtener_pagina(cid, orden, tamano_pagina, token=None):
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
            "GetLocalBoqProxy devolvio HTTP %s" % codigo, codigo
        )

    # El endpoint antepone el prefijo anti-XSSI ")]}'" al JSON.
    bruto = cuerpo[4:].lstrip("\n") if cuerpo.startswith(")]}'") else cuerpo
    try:
        datos = json.loads(bruto)
        reseñas = datos[1][10][2]
        siguiente = datos[1][10][6]
    except (IndexError, TypeError, json.JSONDecodeError) as error:
        raise ErrorRecoleccion(
            "la respuesta cambio de estructura (%s): el endpoint fue modificado" % error,
            codigo,
        ) from error

    if not reseñas and token is None:
        raise ErrorRecoleccion(
            "HTTP 200 con la lista vacia: el endpoint fue retirado",
            codigo,
        )
    return reseñas, siguiente


def limpiar_texto(valor):
    """Convierte los ``<br>`` en saltos de línea y decodifica entidades HTML."""
    if not isinstance(valor, str):
        return ""
    valor = re.sub(r"<br\s*/?>", "\n", valor, flags=re.I)
    return html.unescape(valor).strip()


def extraer_campos(reseña):
    """Mapea los índices posicionales del JSON a campos con nombre."""
    fecha_lista = reseña[2] if len(reseña) > 2 and isinstance(reseña[2], list) else None
    autor_lista = reseña[3] if len(reseña) > 3 and isinstance(reseña[3], list) else None

    # El texto aparece en varios índices; se prefiere 27, luego 28 y luego 11.
    texto = ""
    for indice in (27, 28, 11):
        if indice < len(reseña) and isinstance(reseña[indice], str) and reseña[indice].strip():
            texto = limpiar_texto(reseña[indice])
            break

    return {
        "estrellas": reseña[1] if len(reseña) > 1 else None,
        "fecha": (fecha_lista or [None])[0] if fecha_lista else None,
        "autor": (autor_lista or [None])[0] if autor_lista else None,
        "id": reseña[5] if len(reseña) > 5 else "",
        "texto": texto,
    }


def obtener_resenas(consulta, orden=2, tamano_pagina=20, max_paginas=6, max_resenas=100):
    """Recorre las páginas de un lugar, deduplicando por review ID.

    Devuelve (lista_de_reseñas, cid_utilizado).
    """
    cids = obtener_cids(consulta)
    if not cids:
        raise ErrorRecoleccion("la busqueda no devolvio ningun CID valido")

    for cid in cids[:4]:
        vistas, salida, token, pagina = set(), [], None, 0
        while pagina < max_paginas and len(salida) < max_resenas:
            reseñas, token = obtener_pagina(cid, orden, tamano_pagina, token)
            nuevas = 0
            for reseña in reseñas:
                campos = extraer_campos(reseña)
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
            return salida, cid
        # CID valido pero sin reseñas: se prueba el siguiente candidato.
        time.sleep(PAUSA_ENTRE_CANDIDATOS)

    raise ErrorRecoleccion(
        "ninguno de los %d CID candidatos devolvio resenas" % min(len(cids), 4)
    )


def resumen_distribucion(reseñas):
    """Histograma de estrellas, que la API oficial de Places no expone."""
    conteo = {}
    for reseña in reseñas:
        estrellas = reseña["estrellas"]
        if estrellas is not None:
            conteo[estrellas] = conteo.get(estrellas, 0) + 1
    return dict(sorted(conteo.items(), reverse=True))


def extraer_negativas(reseñas, cantidad):
    """Las N reseñas negativas más recientes que tengan texto.

    Las reseñas sin cuerpo se descartan para que no consuman una de las plazas.
    """
    return [
        reseña
        for reseña in reseñas
        if reseña["estrellas"] is not None and reseña["estrellas"] <= 2 and reseña["texto"]
    ][:cantidad]


def correr_smoke_test():
    """Verifica los tres pasos de `docs/fuente-de-resenas.md` sobre un negocio conocido."""
    objetivo = "robstudiofit Talcahuano"
    fallos = []

    print("Smoke test contra: %s" % objetivo)
    print()

    # 1. El paso 1 debe devolver al menos un CID.
    try:
        cids = obtener_cids(objetivo)
        if cids:
            print("  [OK]   paso 1 -> %d CID candidatos" % len(cids))
        else:
            fallos.append("el paso 1 no devolvio ningun CID")
            print("  [FALLO] paso 1 -> sin CID")
    except ErrorRecoleccion as error:
        fallos.append(str(error))
        print("  [FALLO] paso 1 -> %s" % error)

    # 2. El paso 2 debe devolver reseñas sin que el payload falle.
    try:
        reseñas, cid = obtener_resenas(objetivo, orden=2, max_paginas=6, max_resenas=100)
        print("  [OK]   paso 2 -> %d resenas unicas (cid %s)" % (len(reseñas), cid))

        # 3. La cantidad debe coincidir con la que muestra Google Maps.
        print("         paso 3 -> comparar manualmente contra Google Maps")
        print()
        print("  Distribucion: %s" % resumen_distribucion(reseñas))
    except ErrorRecoleccion as error:
        fallos.append(str(error))
        print("  [FALLO] paso 2 -> %s" % error)

    print()
    if fallos:
        print("SMOKE TEST FALLIDO: %s" % "; ".join(fallos))
        return 1
    print("SMOKE TEST OK")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Recolecta reseñas de Google Maps sin navegador.",
        epilog="Contrato documentado en docs/fuente-de-resenas.md",
    )
    parser.add_argument(
        "consulta",
        nargs="?",
        help='nombre del negocio, por ejemplo "Clínica Cotocollao Quito"',
    )
    parser.add_argument(
        "--sort",
        type=int,
        choices=sorted(ORDENES),
        default=2,
        help="orden de las reseñas (por defecto 2, las mas recientes)",
    )
    parser.add_argument(
        "--max-paginas",
        type=int,
        default=6,
        help="cantidad maxima de paginas a pedir (por defecto 6)",
    )
    parser.add_argument(
        "--max-resenas",
        type=int,
        default=100,
        help="cantidad maxima de resenas a acumular (por defecto 100)",
    )
    parser.add_argument(
        "--negativas",
        type=int,
        default=5,
        help="cantidad de resenas negativas a destacar (por defecto 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="imprime JSON en vez de texto legible",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="verifica que el endpoint sigue respondiendo",
    )
    args = parser.parse_args()

    if args.smoke_test:
        sys.exit(correr_smoke_test())

    if not args.consulta:
        parser.error("falta la consulta; use --smoke-test para verificar el endpoint")

    inicio = time.time()
    try:
        reseñas, cid = obtener_resenas(
            args.consulta,
            orden=args.sort,
            max_paginas=args.max_paginas,
            max_resenas=args.max_resenas,
        )
    except ErrorRecoleccion as error:
        print("FALLO: %s" % error, file=sys.stderr)
        sys.exit(1)
    transcurrido = time.time() - inicio

    negativas = extraer_negativas(reseñas, args.negativas)

    if args.json:
        print(
            json.dumps(
                {
                    "consulta": args.consulta,
                    "cid": cid,
                    "orden": args.sort,
                    "total": len(reseñas),
                    "distribucion": resumen_distribucion(reseñas),
                    "duplicados": len(reseñas) - len({r["id"] for r in reseñas if r["id"]}),
                    "negativas": negativas,
                    "reseñas": reseñas,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print("Consulta   : %s" % args.consulta)
    print("CID        : %s" % cid)
    print("Orden      : %d (%s)" % (args.sort, ORDENES[args.sort]))
    print("Reseñas    : %d únicas en %.1f s" % (len(reseñas), transcurrido))
    print("Duplicados : %d" % (len(reseñas) - len({r["id"] for r in reseñas if r["id"]})))
    print("Distribución: %s" % resumen_distribucion(reseñas))

    print()
    print("--- Primeras reseñas en el orden recibido ---")
    for reseña in reseñas[:5]:
        texto = (reseña["texto"] or "(sin texto)")[:160].replace("\n", " / ")
        print("  %s est | %s | %s" % (reseña["estrellas"], reseña["fecha"], reseña["autor"]))
        print("     %s" % texto)

    print()
    print("=== %d RESEÑAS NEGATIVAS MÁS RECIENTES (<=2 estrellas, con texto) ===" % args.negativas)
    if not negativas:
        print("  (ninguna — el negocio no tiene)")
    for indice, reseña in enumerate(negativas, 1):
        print("  %d. %s est | %s | %s" % (indice, reseña["estrellas"], reseña["fecha"], reseña["autor"]))
        print("     %s" % reseña["texto"][:300].replace("\n", " "))


if __name__ == "__main__":
    main()
