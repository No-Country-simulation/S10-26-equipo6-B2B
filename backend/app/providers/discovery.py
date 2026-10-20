"""Discovery de negocios por rubro y ciudad via SerpApi Google Maps.

Fuente primaria verificada del equipo; contrato completo en
docs/fuente-de-discovery.md. Decisiones que bajan de ese documento:

- la consulta se arma como ``"<rubro> en <ciudad>"`` (la ciudad va en la query)
- los filtros del brief se aplican post-fetch: rating < 3.5 y resenas > 10
- un resultado sin metricas o sin ``place_id`` no es un lead evaluable
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.schemas.discovery import Negocio

Transporte = Callable[[str], tuple[str, int]]

URL_SERPAPI = "https://serpapi.com/search"


class DiscoveryError(Exception):
    """Fallo recuperable del discovery, con mensaje accionable."""

    def __init__(self, mensaje: str, codigo: int | None = None):
        super().__init__(mensaje)
        self.codigo = codigo


def _http_get(url: str, timeout: int = 60) -> tuple[str, int]:
    """GET con urllib; devuelve (cuerpo, codigo). Nunca lanza por HTTP inesperado."""
    peticion = urllib.request.Request(url, headers={"User-Agent": "repusense-backend/0.1"})
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return respuesta.read().decode("utf-8", "replace"), respuesta.status
    except urllib.error.HTTPError as error:
        return error.read().decode("utf-8", "replace"), error.code
    except Exception as error:  # se reporta al caller como codigo 0
        return f"EXC:{error}", 0


class SerpApiDiscovery:
    """Obtiene negocios por rubro y ciudad aplicando los filtros del brief."""

    def __init__(
        self,
        transporte: Transporte | None = None,
        *,
        api_key: str | None = None,
        espera_s: float | None = None,
        max_paginas: int | None = None,
    ) -> None:
        self._transporte = transporte or _http_get
        self._api_key = settings.serpapi_key if api_key is None else api_key
        self._espera_s = settings.discovery_request_interval if espera_s is None else espera_s
        self._max_paginas = (
            settings.discovery_max_paginas if max_paginas is None else max_paginas
        )

    def buscar_negocios(self, rubro: str, ciudad: str) -> list[Negocio]:
        """Devuelve los negocios de rubro+ciudad que cumplen los filtros.

        Pagina con ``serpapi_pagination.next`` hasta agotar resultados o
        llegar a ``max_paginas``: la pagina 1 por relevancia trae a los mejor
        puntuados, los leads viven en paginas profundas
        (hallazgo medido en docs/fuente-de-discovery.md).
        """
        if not self._api_key:
            raise DiscoveryError(
                "falta SERPAPI_KEY: configurarla en backend/.env "
                "(ver docs/fuente-de-discovery.md)"
            )
        encontrados: list[Negocio] = []
        start = 0
        for pagina in range(self._max_paginas):
            if pagina and self._espera_s > 0:
                time.sleep(self._espera_s)  # cortesia: 50 busquedas/hora en free tier
            datos = self._pedir_pagina(rubro, ciudad, start)
            resultados = datos.get("local_results") or []
            if not resultados:
                break
            encontrados.extend(self._normalizar_y_filtrar(resultados))
            siguiente = (datos.get("serpapi_pagination") or {}).get("next")
            if not siguiente:
                break
            start += 20
        return encontrados

    def _pedir_pagina(self, rubro: str, ciudad: str, start: int = 0) -> dict[str, Any]:
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": f"{rubro} en {ciudad}",
            "hl": "es-419",
            "gl": settings.discovery_gl,
            "api_key": self._api_key,
        }
        if start:
            params["start"] = str(start)
        url = URL_SERPAPI + "?" + urllib.parse.urlencode(params)
        cuerpo, codigo = self._transporte(url)
        if codigo != 200:
            raise DiscoveryError(
                f"SerpApi devolvio HTTP {codigo}: revisar key/cuota "
                "(senales de fallo en docs/fuente-de-discovery.md)",
                codigo,
            )
        try:
            datos: dict[str, Any] = json.loads(cuerpo)
        except json.JSONDecodeError as error:
            raise DiscoveryError(f"la respuesta de SerpApi no es JSON: {error}") from error
        if "error" in datos:
            raise DiscoveryError(f"SerpApi reporto error: {datos['error']}")
        return datos

    def _normalizar_y_filtrar(self, resultados: list[dict[str, Any]]) -> list[Negocio]:
        salida: list[Negocio] = []
        for resultado in resultados:
            rating = resultado.get("rating")
            reviews = resultado.get("reviews")
            place_id = resultado.get("place_id")
            if rating is None or reviews is None or not place_id:
                continue
            if not (
                rating < settings.discovery_max_rating
                and reviews > settings.discovery_min_reviews
            ):
                continue
            salida.append(
                Negocio(
                    nombre=resultado.get("title") or "",
                    rating=float(rating),
                    total_resenas=int(reviews),
                    place_id=place_id,
                    telefono=resultado.get("phone"),
                    website=resultado.get("website"),
                    direccion=resultado.get("address"),
                    rubro=resultado.get("type"),
                    estado_operativo=resultado.get("business_status"),
                )
            )
        return salida
