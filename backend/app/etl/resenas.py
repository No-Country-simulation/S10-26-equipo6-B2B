"""CLI de compatibilidad y punto de entrada para reseñas de Google Maps.

Implementación de referencia del contrato documentado en
`docs/fuente-de-resenas.md`. Expone la interfaz de consola y el smoke test,
delegando el acceso al cliente de infraestructura
(``app.infrastructure.external.google_maps_client``).
"""

import argparse
import json
import sys
import time

from app.infrastructure.external import google_maps_client
from app.infrastructure.external.google_maps_client import (
    HEADERS,
    ORDENES,
    PAUSA_ENTRE_CANDIDATOS,
    PAUSA_ENTRE_PAGINAS,
    URL_BUSQUEDA,
    URL_RESENAS,
    USER_AGENT,
    ErrorRecoleccion,
    GoogleMapsClient,
    GoogleMapsError,
    construir_payload,
    extraer_campos,
    extraer_cid,
    extraer_negativas,
    http_get,
    limpiar_texto,
    obtener_cids,
    obtener_negativas,
    obtener_pagina,
    obtener_resenas,
    parsear_cid,
    parsear_epoch_ms,
    resumen_distribucion,
)


def correr_smoke_test() -> int:
    """Verifica los tres pasos de docs/fuente-de-resenas.md sobre un negocio conocido."""
    objetivo = "robstudiofit Talcahuano"
    fallos: list[str] = []

    print(f"Smoke test contra: {objetivo}\n")

    # 1. El paso 1 debe devolver al menos un CID.
    try:
        cids = obtener_cids(objetivo)
        if cids:
            print(f"  [OK]   paso 1 -> {len(cids)} CID candidatos")
        else:
            fallos.append("el paso 1 no devolvio ningun CID")
            print("  [FALLO] paso 1 -> sin CID")
    except ErrorRecoleccion as error:
        fallos.append(str(error))
        print(f"  [FALLO] paso 1 -> {error}")

    # 2. El paso 2 debe devolver reseñas sin que el payload falle.
    try:
        reseñas, cid = obtener_resenas(objetivo, orden=2, max_paginas=6, max_resenas=100)
        print(f"  [OK]   paso 2 -> {len(reseñas)} resenas unicas (cid {cid})")

        # 3. La cantidad debe coincidir con la que muestra Google Maps.
        print("         paso 3 -> comparar manualmente contra Google Maps\n")
        print(f"  Distribucion: {resumen_distribucion(reseñas)}")
    except ErrorRecoleccion as error:
        fallos.append(str(error))
        print(f"  [FALLO] paso 2 -> {error}")

    print()
    if fallos:
        print(f"SMOKE TEST FALLIDO: {'; '.join(fallos)}")
        return 1
    print("SMOKE TEST OK")
    return 0


def main(argv: list[str] | None = None) -> None:
    # Las consolas de Windows usan cp1252 por defecto y arruinan los acentos.
    sys.stdout.reconfigure(encoding="utf-8")

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
    args = parser.parse_args(argv)

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
        print(f"FALLO: {error}", file=sys.stderr)
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

    print(f"Consulta   : {args.consulta}")
    print(f"CID        : {cid}")
    print(f"Orden      : {args.sort} ({ORDENES[args.sort]})")
    print(f"Reseñas    : {len(reseñas)} únicas en {transcurrido:.1f} s")
    print(f"Duplicados : {len(reseñas) - len({r['id'] for r in reseñas if r['id']})}")
    print(f"Distribución: {resumen_distribucion(reseñas)}\n")

    print("--- Primeras reseñas en el orden recibido ---")
    for reseña in reseñas[:5]:
        texto = (reseña["texto"] or "(sin texto)")[:160].replace("\n", " / ")
        print(f"  {reseña['estrellas']} est | {reseña['fecha']} | {reseña['autor']}")
        print(f"     {texto}")

    print(
        f"\n=== {args.negativas} RESEÑAS NEGATIVAS MÁS RECIENTES (<= 3 estrellas, con texto) ==="
    )
    if not negativas:
        print("  (ninguna — el negocio no tiene)")
    for indice, reseña in enumerate(negativas, 1):
        print(
            f"  {indice}. {reseña['estrellas']} est | {reseña['fecha']} | {reseña['autor']}"
        )
        print(f"     {reseña['texto'][:300].replace('\n', ' ')}")


__all__ = [
    "HEADERS",
    "ORDENES",
    "PAUSA_ENTRE_CANDIDATOS",
    "PAUSA_ENTRE_PAGINAS",
    "URL_BUSQUEDA",
    "URL_RESENAS",
    "USER_AGENT",
    "ErrorRecoleccion",
    "GoogleMapsClient",
    "GoogleMapsError",
    "construir_payload",
    "correr_smoke_test",
    "extraer_campos",
    "extraer_cid",
    "extraer_negativas",
    "google_maps_client",
    "http_get",
    "limpiar_texto",
    "main",
    "obtener_cids",
    "obtener_negativas",
    "obtener_pagina",
    "obtener_resenas",
    "parsear_cid",
    "parsear_epoch_ms",
    "resumen_distribucion",
]


if __name__ == "__main__":
    main()

