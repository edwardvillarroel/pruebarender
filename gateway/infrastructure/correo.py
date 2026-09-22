"""Envío de correos del gateway vía la REST API de EmailJS.

Para pasar el envío de MOCK a real, completar en `.env`:
    EMAILJS_PUBLIC_KEY, EMAILJS_PRIVATE_KEY, EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID

Además, en el dashboard de EmailJS:
- La plantilla debe usar las variables {{to_email}} y {{codigo}}.
- Activar "Allow API for non-browser applications" (llamadas desde el servidor).
- Si está habilitado "Use Private Key", el campo `accessToken` es obligatorio.
"""
import httpx

from gateway.config import Config

EMAILJS_URL = "https://api.emailjs.com/api/v1.0/email/send"


class ErrorEnvioCorreo(Exception):
    """Falla al enviar el correo (red o respuesta no 2xx de EmailJS)."""


def configurado_emailjs() -> bool:
    """True cuando hay credenciales de EmailJS configuradas (envío real)."""
    return bool(
        Config.EMAILJS_PRIVATE_KEY
        and Config.EMAILJS_SERVICE_ID
        and Config.EMAILJS_TEMPLATE_ID
    )


def enviar_correo_codigo(email: str, codigo: str) -> None:
    """Envía el código de verificación por correo.

    Sin credenciales configuradas no hace nada (el flujo queda en MOCK).
    Con credenciales, lanza ErrorEnvioCorreo si el envío falla.
    """
    if not configurado_emailjs():
        return

    payload = {
        "service_id": Config.EMAILJS_SERVICE_ID,
        "template_id": Config.EMAILJS_TEMPLATE_ID,
        "user_id": Config.EMAILJS_PUBLIC_KEY,
        "accessToken": Config.EMAILJS_PRIVATE_KEY,
        "template_params": {
            "to_email": email,
            "codigo": codigo,
        },
    }

    try:
        respuesta = httpx.post(EMAILJS_URL, json=payload, timeout=15)
    except httpx.HTTPError as error:
        raise ErrorEnvioCorreo(f"Error de red al enviar el correo: {error}") from error

    if respuesta.status_code >= 400:
        raise ErrorEnvioCorreo(
            f"EmailJS respondió {respuesta.status_code}: {respuesta.text[:300]}"
        )