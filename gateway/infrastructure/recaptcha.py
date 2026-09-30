"""Verificación de reCAPTCHA v2 contra la API de Google.

Solo se exige cuando `RECAPTCHA_SECRET_KEY` está configurada en `.env`; sin keys
la validación se omite (modo dev) y `verificacion_requerida` devuelve False.
"""
import httpx

from gateway.config import Config

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verificacion_requerida() -> bool:
    """True cuando hay secret key configurada (el captcha debe validarse)."""
    return bool(Config.RECAPTCHA_SECRET_KEY)


def verificar_token(token: str) -> bool:
    """Valida el token del frontend contra Google. Muta el estado del captcha.

    Seguridad: el token de reCAPTCHA es de UN solo uso; Google lo invalida tras
    verificar, por lo que cada intento de login debe presentar un token nuevo.
    """
    if not token:
        return False
    if not verificacion_requerida():
        # Sin keys el captcha no se puede validar: no bloquear el flujo (dev).
        return bool(token)
    try:
        respuesta = httpx.post(
            RECAPTCHA_VERIFY_URL,
            data={
                "secret": Config.RECAPTCHA_SECRET_KEY,
                "response": token,
            },
            timeout=10,
        )
        datos = respuesta.json()
    except httpx.HTTPError:
        return False
    return bool(datos.get("success"))