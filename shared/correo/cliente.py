"""Cliente mínimo para la API HTTP de Resend.

El envío es best-effort desde el punto de vista del llamador: si no hay
credenciales se simula sin lanzar, y los errores de red se reintentan una vez.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

from shared.correo.modelos import Correo

logger = logging.getLogger(__name__)

URL_RESEND = "https://api.resend.com/emails"
TIEMPO_ESPERA_SEGUNDOS = 15
REINTENTO_ESPERA_SEGUNDOS = 0.5
USER_AGENT = "ApoloVibes/1.0"


class ErrorEnvioCorreo(Exception):
    """Error controlado al enviar un correo por Resend."""


def _leer_config(config: Any, nombre: str) -> str:
    if config is None:
        return ""
    if isinstance(config, Mapping):
        valor = config.get(nombre, "")
    else:
        valor = getattr(config, nombre, "")
    return str(valor or "").strip()


def _dominio(destino: str) -> str:
    _, _, dominio = destino.partition("@")
    return dominio or "desconocido"


def _redactar(texto: str) -> str:
    """Evita devolver direcciones de correo en los mensajes de error."""
    palabras = []
    for palabra in str(texto).split():
        if "@" in palabra:
            usuario, _, dominio = palabra.partition("@")
            palabras.append(f"{usuario[:1]}***@{dominio}" if usuario else "***")
        else:
            palabras.append(palabra)
    return " ".join(palabras)[:300]


def _detalle_error(respuesta: httpx.Response) -> tuple[str, str]:
    try:
        datos = respuesta.json()
    except (ValueError, json.JSONDecodeError):
        return "", ""
    if not isinstance(datos, dict):
        return "", ""
    nombre = _redactar(datos.get("name") or "")
    mensaje = _redactar(datos.get("message") or "")
    return str(nombre), str(mensaje)


def _error_http(status: int, respuesta: httpx.Response) -> ErrorEnvioCorreo:
    nombre, mensaje = _detalle_error(respuesta)
    detalle = f"Resend respondió {status}"
    if nombre:
        detalle += f" ({nombre})"
    if mensaje:
        detalle += f": {mensaje}"
    return ErrorEnvioCorreo(detalle)


class ClienteCorreo:
    """Cliente de Resend con modo simulación cuando falta configuración."""

    def __init__(self, config: Any) -> None:
        self._api_key = _leer_config(config, "RESEND_API_KEY")
        self._remitente = _leer_config(config, "EMAIL_FROM")

    @property
    def configurado(self) -> bool:
        return bool(self._api_key and self._remitente)

    def _cabeceras(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def enviar(self, destino: str, correo: Correo) -> bool:
        """Envía un correo. Devuelve False en modo simulación."""
        if not self.configurado:
            logger.info(
                "Correo simulado (Resend sin credenciales) hacia dominio %s: %s",
                _dominio(destino),
                correo.asunto,
            )
            return False

        datos = {
            "from": self._remitente,
            "to": [destino],
            "subject": correo.asunto,
            "html": correo.html,
            "text": correo.texto,
        }

        try:
            respuesta = httpx.post(
                URL_RESEND,
                json=datos,
                headers=self._cabeceras(),
                timeout=TIEMPO_ESPERA_SEGUNDOS,
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            logger.warning(
                "Fallo transitorio de Resend hacia dominio %s: %s",
                _dominio(destino),
                type(error).__name__,
            )
            time.sleep(REINTENTO_ESPERA_SEGUNDOS)
            try:
                respuesta = httpx.post(
                    URL_RESEND,
                    json=datos,
                    headers=self._cabeceras(),
                    timeout=TIEMPO_ESPERA_SEGUNDOS,
                )
            except (httpx.TimeoutException, httpx.TransportError) as reintento:
                raise ErrorEnvioCorreo(
                    f"Resend no respondió tras reintentar ({type(reintento).__name__})"
                ) from reintento
        except httpx.HTTPError as error:
            raise ErrorEnvioCorreo(
                f"Error de conexión con Resend ({type(error).__name__})"
            ) from error

        if 500 <= respuesta.status_code <= 599:
            logger.warning(
                "Resend respondió %s hacia dominio %s; reintentando",
                respuesta.status_code,
                _dominio(destino),
            )
            time.sleep(REINTENTO_ESPERA_SEGUNDOS)
            try:
                respuesta = httpx.post(
                    URL_RESEND,
                    json=datos,
                    headers=self._cabeceras(),
                    timeout=TIEMPO_ESPERA_SEGUNDOS,
                )
            except (httpx.TimeoutException, httpx.TransportError) as reintento:
                raise ErrorEnvioCorreo(
                    f"Resend no respondió tras reintentar ({type(reintento).__name__})"
                ) from reintento
            except httpx.HTTPError as error:
                raise ErrorEnvioCorreo(
                    f"Error de conexión con Resend ({type(error).__name__})"
                ) from error

        if respuesta.status_code == 200:
            return True

        raise _error_http(respuesta.status_code, respuesta)
