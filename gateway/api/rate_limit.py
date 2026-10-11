
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _ip_real() -> str:
    """Clave de rate limit tras el proxy de Render.

    Detrás del proxy TODOS los clientes comparten la IP del proxy, así que
    usar get_remote_address haría que los límites (login 20/min, refresh
    10/min, MFA 10/min) fueran GLOBALES. Se toma la ÚLTIMA IP de
    X-Forwarded-For (la que appendea el proxy de Render); nunca la primera,
    que es la que el cliente puede falsificar. Sin header: fallback a la IP
    remota directa.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ultima = forwarded.split(",")[-1].strip()
        if ultima:
            return ultima
    return get_remote_address()


limiter = Limiter(key_func=_ip_real)
