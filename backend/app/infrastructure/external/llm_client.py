"""Cliente de inferencia LLM para clasificación de reseñas y redacción de cold emails.

Satisface ``AIProviderProtocol`` (DIP). Funciona con cualquier endpoint compatible
con OpenAI y cuenta con un generador heurístico determinista como fallback offline
cuando no hay API key configurada o durante ejecuciones de prueba.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.schemas.ai import (
    CATALOGO_CATEGORIAS,
    CATEGORIA_FALLBACK,
    AIAnalysisResult,
)

logger = logging.getLogger(__name__)

TransporteHttp = Callable[[str, dict[str, str], bytes], tuple[str, int]]

URL_OPENAI_DEFAULT = "https://api.openai.com/v1/chat/completions"


class LLMClient:
    """Proveedor de inferencia de IA con tolerancia a fallos y modo heurístico offline."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = URL_OPENAI_DEFAULT,
        transport: TransporteHttp | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.ai_model or "gpt-4o-mini"
        self.base_url = base_url
        self.transport = transport

    def analizar_resenas(
        self,
        nombre_negocio: str,
        rubro: str,
        resenas: list[str],
    ) -> AIAnalysisResult:
        """Clasifica los puntos de dolor y genera la propuesta comercial de cold email."""
        if self.api_key:
            try:
                return self._analizar_con_llm(nombre_negocio, rubro, resenas)
            except Exception as error:
                logger.warning(
                    "Fallo al invocar el LLM para %r: %s. Utilizando clasificador heurístico.",
                    nombre_negocio,
                    error,
                )

        return self._analizar_con_heuristica(nombre_negocio, rubro, resenas)

    def _analizar_con_llm(
        self,
        nombre_negocio: str,
        rubro: str,
        resenas: list[str],
    ) -> AIAnalysisResult:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un analista experto de reputación comercial B2B para RepuSense. "
                        "Analiza las reseñas negativas del negocio y devuelve un JSON estricto "
                        "con las siguientes claves: 'category', 'pain_points_summary', "
                        "'email_subject', 'email_first_paragraph'. "
                        f"La clave 'category' debe ser una de: {', '.join(CATALOGO_CATEGORIAS)}."
                    ),
                },
                {
                    "role": "user",
                    "content": self._construir_prompt(nombre_negocio, rubro, resenas),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        cuerpo_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "repusense-backend/0.1",
        }

        if self.transport is not None:
            cuerpo_resp, status = self.transport(self.base_url, headers, cuerpo_bytes)
        else:
            cuerpo_resp, status = self._post_http(self.base_url, headers, cuerpo_bytes)

        if status != 200:
            raise RuntimeError(f"El LLM devolvió status HTTP {status}: {cuerpo_resp[:200]}")

        datos = json.loads(cuerpo_resp)
        contenido_str = datos["choices"][0]["message"]["content"]
        resultado_json: dict[str, Any] = json.loads(contenido_str)
        resultado_json["ai_model"] = self.model
        return AIAnalysisResult.model_validate(resultado_json)

    def _analizar_con_heuristica(
        self,
        nombre_negocio: str,
        rubro: str,
        resenas: list[str],
    ) -> AIAnalysisResult:
        categoria = self._clasificar_por_palabras_clave(resenas)
        cat_lower = categoria.lower()
        puntos_dolor = (
            f"Los clientes señalan dificultades principalmente relacionadas con {cat_lower}, "
            "destacando inconsistencias en el servicio y áreas de mejora recurrente."
            if resenas
            else "Sin reseñas negativas registradas para este negocio."
        )
        asunto = f"Oportunidad de mejora en {cat_lower} para {nombre_negocio}"
        primer_parrafo = (
            f"Hola equipo de {nombre_negocio}, revisando las opiniones de sus clientes en "
            f"Google Maps, notamos varias menciones constructivas sobre {cat_lower}. "
            "Nos gustaría proponerles una breve estrategia para optimizar la reputación "
            f"en {rubro}."
        )

        return AIAnalysisResult(
            category=categoria,
            pain_points_summary=puntos_dolor,
            email_subject=asunto,
            email_first_paragraph=primer_parrafo,
            ai_model="mock-heuristic-v1",
        )

    def _clasificar_por_palabras_clave(self, resenas: list[str]) -> str:
        if not resenas:
            return CATEGORIA_FALLBACK

        texto = " ".join(resenas).lower()

        criterios = [
            (
                "Atención al cliente",
                [
                    "atencion",
                    "atención",
                    "trato",
                    "grosero",
                    "amabilidad",
                    "personal",
                    "camarero",
                    "mesero",
                    "recepcionista",
                    "empleado",
                    "maleducado",
                ],
            ),
            (
                "Tiempos de espera",
                ["espera", "tarde", "demora", "lento", "lentitud", "tardaron", "fila", "minutos"],
            ),
            (
                "Precios y facturación",
                ["precio", "caro", "costoso", "cobro", "factura", "cuenta", "estafa", "dinero"],
            ),
            (
                "Higiene e instalaciones",
                ["higiene", "sucio", "suciedad", "limpieza", "olor", "baño", "instalaciones"],
            ),
            (
                "Calidad del servicio",
                ["calidad", "mal estado", "frío", "crudo", "defectuoso", "sabor", "comida"],
            ),
        ]

        for categoria, palabras in criterios:
            if any(palabra in texto for palabra in palabras):
                return categoria

        return CATEGORIA_FALLBACK

    def _construir_prompt(self, nombre_negocio: str, rubro: str, resenas: list[str]) -> str:
        bloque_resenas = (
            "\n".join(f"- {r}" for r in resenas)
            if resenas
            else "- Sin reseñas explícitas registradas."
        )
        return (
            f"Negocio: {nombre_negocio}\n"
            f"Rubro: {rubro}\n"
            f"Reseñas negativas recientes:\n{bloque_resenas}\n\n"
            "Analiza las quejas y devuelve el JSON requerido con la categoría controlada "
            "y la propuesta comercial de cold email."
        )

    @staticmethod
    def _post_http(
        url: str,
        headers: dict[str, str],
        data: bytes,
        timeout: int = 45,
    ) -> tuple[str, int]:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace"), resp.status
        except urllib.error.HTTPError as error:
            cuerpo = error.read().decode("utf-8", "replace") if error.fp else ""
            return cuerpo, error.code
        except urllib.error.URLError as error:
            raise RuntimeError(f"Error de conexión con el LLM: {error}") from error
