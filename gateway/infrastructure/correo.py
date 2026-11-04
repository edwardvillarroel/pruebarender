
from gateway.config import Config
from shared.correo import plantillas
from shared.correo.cliente import ClienteCorreo, ErrorEnvioCorreo

__all__ = [
    "ErrorEnvioCorreo",
    "configurado_alerta_login",
    "configurado_correo",
    "enviar_correo_alerta_login",
    "enviar_correo_codigo",
]


def _cliente() -> ClienteCorreo:
    return ClienteCorreo(
        {
            "RESEND_API_KEY": Config.RESEND_API_KEY,
            "EMAIL_FROM": Config.EMAIL_FROM,
        }
    )


def configurado_correo() -> bool:
    """True cuando hay credenciales de Resend configuradas (envío real)."""
    return _cliente().configurado


def enviar_correo_codigo(destino: str, codigo: str, minutos: int = 5) -> None:
    """Envía el código de verificación por correo.

    `minutos` es la vigencia real del código (el mismo TTL que usa el
    gateway), para que el correo no prometa una duración distinta.

    Sin credenciales imprime el código en la consola del servidor (MOCK). Con
    credenciales, lanza `ErrorEnvioCorreo` si el envío falla.
    """
    if not configurado_correo():
        print(
            f"[correo:simulacion] Código de verificación para {destino}: "
            f"{codigo}"
        )
        return
    _cliente().enviar(destino, plantillas.codigo_verificacion(codigo, minutos))


def configurado_alerta_login() -> bool:
    """True cuando se puede enviar la alerta de seguridad."""
    return configurado_correo()


def enviar_correo_alerta_login(destino: str, detalle: str) -> None:
    """Alerta de seguridad (p. ej. varios intentos fallidos de login).

    Lanza `ErrorEnvioCorreo` si el envío falla.
    """
    if not configurado_correo():
        return
    _cliente().enviar(destino, plantillas.alerta_seguridad(detalle))
