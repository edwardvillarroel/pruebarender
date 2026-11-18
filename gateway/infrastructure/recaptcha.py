
import httpx

from gateway.config import Config

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verificacion_requerida() -> bool:
    return bool(Config.RECAPTCHA_SECRET_KEY)


def verificar_token(token: str) -> bool:

    if not token:
        return False
    if not verificacion_requerida():
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