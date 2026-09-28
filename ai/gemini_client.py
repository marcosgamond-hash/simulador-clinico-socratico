# ai/gemini_client.py
"""
Cliente robusto de Gemini para Socrático.
- Usa la API key que pone el residente en el panel lateral
- Reintenta automáticamente si Gemini se satura
- Si falla del todo, devuelve un mensaje socrático de respaldo
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

import streamlit as st
from google import genai
from google.genai import types

from ai.fallbacks import FALLBACK_TURNO_SOCRATICO, FALLBACK_EVALUACION

logger = logging.getLogger("socratico.gemini")

# Modelos que vamos a intentar (en orden de preferencia)
DEFAULT_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


class GeminiClientError(Exception):
    """Error controlado del cliente."""
    pass


def get_api_key() -> str:
    """
    Busca la API key en este orden:
    1. La que el residente pegó en el panel lateral (session_state)
    2. Variables de entorno (por si acaso)
    """
    # 1. La que pone el residente en el sidebar
    key = st.session_state.get("api_key_guardada", "") or st.session_state.get("gemini_api_key", "")
    if key and str(key).strip():
        return str(key).strip()

    # 2. Variables de entorno (opcional)
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key.strip()

    return ""


def create_client(api_key: Optional[str] = None) -> genai.Client:
    """Crea el cliente de Gemini con reintentos configurados."""
    key = (api_key or get_api_key()).strip()
    if not key:
        raise GeminiClientError(
            "No se encontró API Key. Pegá tu clave de Google AI Studio en el panel lateral."
        )

    http_options = types.HttpOptions(
        timeout=90_000,
        retry_options=types.HttpRetryOptions(
            attempts=5,
            initial_delay=1.0,
            max_delay=25.0,
            exp_base=2.0,
            jitter=1.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
    )

    return genai.Client(api_key=key, http_options=http_options)


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(x in msg for x in ("429", "resource_exhausted", "resource exhausted", "quota", "rate limit"))


def _is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(x in msg for x in ("401", "403", "api key", "invalid", "permission", "unauthenticated"))


def generate_content(
    contents: Union[str, List[Any]],
    *,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
    temperature: float = 0.4,
    max_output_tokens: int = 2048,
    tools: Optional[List[Any]] = None,
    api_key: Optional[str] = None,
    max_outer_retries: int = 2,
) -> str:
    """
    Función principal.
    Intenta varias veces y, si todo falla, devuelve el mensaje socrático de respaldo.
    """
    try:
        client = create_client(api_key)
    except GeminiClientError:
        return FALLBACK_TURNO_SOCRATICO

    models_to_try = [model] if model else DEFAULT_MODELS
    models_to_try = [m for m in models_to_try if m]

    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        for attempt in range(max_outer_retries + 1):
            try:
                config_kwargs: Dict[str, Any] = {
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction
                if tools:
                    config_kwargs["tools"] = tools

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(**config_kwargs),
                )

                text = getattr(response, "text", None) or ""
                if text.strip():
                    return text.strip()

                last_error = GeminiClientError("Respuesta vacía del modelo")
                time.sleep(1.5 * (attempt + 1))

            except Exception as e:
                last_error = e
                logger.warning("Error Gemini (model=%s, attempt=%s): %s", model_name, attempt + 1, str(e)[:250])

                if _is_auth_error(e):
                    return (
                        "Comité Médico Evaluador: La API Key parece inválida o sin permisos. "
                        "Verificá la clave que pegaste en el panel lateral (Google AI Studio)."
                    )

                if _is_rate_limit_error(e):
                    time.sleep(min(8.0 * (2 ** attempt), 22.0))
                else:
                    time.sleep(1.5 * (attempt + 1))

    # Si llegamos acá, todo falló → mensaje de respaldo
    logger.error("Todos los intentos fallaron. Último error: %s", last_error)
    return FALLBACK_TURNO_SOCRATICO
