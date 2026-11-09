"""Extractor de correos electrónicos desde sitios web de negocios (RF3).

Satisface ``ContactEnricherProtocol`` (DIP). Rastrea la página de inicio y rutas
comunes de contacto (/contacto, /nosotros) mediante HTTP nativo con timeouts
estrictos y tolerancia completa a fallos de red o sitios caídos.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

logger = logging.getLogger(__name__)

MAX_HTML_BYTES_DEFAULT = 512 * 1024  # 512 KB máximo por página para prevenir DoS
HOSTS_BLOQUEADOS = {"localhost", "localhost.localdomain", "metadata.google.internal"}

TransporteHttp = Callable[[str], tuple[str, int]]

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")

# Extensiones de assets y dominios plantilla que no corresponden a correos reales
EXTENSIONES_INVALIDAS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "svg",
    "webp",
    "css",
    "js",
    "woff",
    "woff2",
    "ttf",
}
DOMINIOS_DESCARTADOS = {
    "example.com",
    "ejemplo.com",
    "dominio.com",
    "test.com",
    "sentry.io",
    "wixpress.com",
    "wordpress.org",
    "schema.org",
    "gravatar.com",
}

RUTAS_CONTACTO = ["/contacto", "/contact", "/nosotros", "/about"]


class WebsiteScraper:
    """Cliente HTTP liviano para extraer correos electrónicos de un sitio web."""

    def __init__(
        self,
        timeout: float = 6.0,
        transport: TransporteHttp | None = None,
        max_subpaginas: int = 2,
        max_bytes: int = MAX_HTML_BYTES_DEFAULT,
    ) -> None:
        self.timeout = timeout
        self.transport = transport
        self.max_subpaginas = max_subpaginas
        self.max_bytes = max_bytes

    def extraer_emails(self, url_web: str) -> list[str]:
        """Explora la web del negocio y devuelve correos electrónicos válidos normalizados."""
        url_normalizada = self._normalizar_url(url_web)
        if not url_normalizada:
            return []

        emails_encontrados: list[str] = []
        visitadas: set[str] = set()

        # 1. Explorar página principal
        html_home = self._obtener_html(url_normalizada)
        visitadas.add(url_normalizada)
        if html_home:
            for email in self._extraer_de_texto(html_home):
                if email not in emails_encontrados:
                    emails_encontrados.append(email)

        # Si ya se encontraron correos en la home, no es necesario saturar con subpáginas
        if emails_encontrados:
            return emails_encontrados

        # 2. Explorar subpáginas de contacto frecuentes
        subpaginas_exploradas = 0
        for ruta in RUTAS_CONTACTO:
            if subpaginas_exploradas >= self.max_subpaginas:
                break

            url_subpagina = urllib.parse.urljoin(url_normalizada, ruta)
            if url_subpagina in visitadas:
                continue

            visitadas.add(url_subpagina)
            html_sub = self._obtener_html(url_subpagina)
            if html_sub:
                subpaginas_exploradas += 1
                for email in self._extraer_de_texto(html_sub):
                    if email not in emails_encontrados:
                        emails_encontrados.append(email)

            if emails_encontrados:
                break

        return emails_encontrados

    def _obtener_html(self, url: str) -> str | None:
        """Descarga el contenido de la URL con timeout o usa el transporte de prueba."""
        if self.transport is not None:
            try:
                cuerpo, status = self.transport(url)
                return cuerpo if status == 200 else None
            except Exception as error:
                logger.debug("Error en transporte mock para %s: %s", url, error)
                return None

        # Anti-SSRF: valida esquema, hostname y resolución IP antes de abrir socket
        if not self._es_url_segura(url):
            return None

        peticion = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 RepuSense/0.1"
                ),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                tipo_contenido = respuesta.headers.get("Content-Type", "").lower()
                if "text/html" not in tipo_contenido and "text/plain" not in tipo_contenido:
                    return None
                # Límite Anti-DoS: evita picos de memoria por respuestas HTML masivas
                return respuesta.read(self.max_bytes).decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
            logger.debug("No se pudo obtener contenido de %s: %s", url, error)
            return None
        except Exception as error:
            logger.warning("Fallo inesperado al raspar %s: %s", url, error)
            return None

    @classmethod
    def _es_url_segura(cls, url: str) -> bool:
        """Anti-SSRF: valida esquema HTTP/HTTPS y bloquea IPs privadas, loopback y metadatos."""
        try:
            parseado = urllib.parse.urlparse(url)
            if parseado.scheme not in ("http", "https"):
                logger.warning("Bloqueo SSRF: esquema no permitido en URL: %r", url)
                return False

            host = parseado.hostname
            if not host:
                return False

            host_lower = host.lower()
            if host_lower in HOSTS_BLOQUEADOS:
                logger.warning("Bloqueo SSRF: hostname prohibido: %r", host)
                return False

            # Si el host es una IP literal
            try:
                ip = ipaddress.ip_address(host_lower)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                ):
                    logger.warning("Bloqueo SSRF: IP privada/prohibida (%s) para URL: %r", ip, url)
                    return False
            except ValueError:
                # Es un nombre de dominio; resolvemos DNS para verificar la IP destino
                try:
                    direcciones = socket.getaddrinfo(host_lower, None)
                    for _, _, _, _, sockaddr in direcciones:
                        ip_str = sockaddr[0]
                        ip = ipaddress.ip_address(ip_str)
                        if (
                            ip.is_private
                            or ip.is_loopback
                            or ip.is_link_local
                            or ip.is_multicast
                            or ip.is_reserved
                        ):
                            logger.warning(
                                "Bloqueo SSRF: el dominio %r resolvió a IP prohibida %s",
                                host,
                                ip,
                            )
                            return False
                except (socket.gaierror, OSError):
                    # En entornos sin resolución DNS (ej. CI/CD o sandbox offline),
                    # no bloqueamos preventivamente si no es host prohibido ni IP literal.
                    logger.debug("Sin resolución DNS para %r en verificación preventiva", host)
                    return True

            return True
        except Exception as err:
            logger.warning("Error al validar seguridad de URL %r: %s", url, err)
            return False

    def _extraer_de_texto(self, texto: str) -> list[str]:
        """Aplica regex y descarta falsos positivos o archivos estáticos."""
        candidatos = EMAIL_REGEX.findall(texto)
        validos: list[str] = []

        for cand in candidatos:
            email = cand.lower().strip()
            if not self._es_email_valido(email):
                continue
            if email not in validos:
                validos.append(email)

        return validos

    @staticmethod
    def _es_email_valido(email: str) -> bool:
        if "@" not in email:
            return False

        usuario, dominio = email.split("@", 1)
        if not usuario or not dominio:
            return False

        if dominio in DOMINIOS_DESCARTADOS:
            return False

        partes_dominio = dominio.split(".")
        tld = partes_dominio[-1].lower()
        if tld in EXTENSIONES_INVALIDAS:
            return False

        # Descartar secuencias comunes de placeholder
        return not any(token in email for token in ("username", "yourname", "domain", "ejemplo"))

    @staticmethod
    def _normalizar_url(url: str) -> str | None:
        if not url:
            return None
        limpia = url.strip()
        if not limpia:
            return None
        if not (limpia.startswith("http://") or limpia.startswith("https://")):
            limpia = f"https://{limpia}"
        return limpia
