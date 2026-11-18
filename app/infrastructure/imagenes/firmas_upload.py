

from __future__ import annotations

import hashlib
import hmac
import time

from flask import current_app

_VENTANA_SEGUNDOS = 3600


def firmar(ruta: str | None) -> str | None:
    if ruta is None:
        return None
    if ruta.startswith(("http://", "https://")):
        return ruta
    normalizada = ruta.replace("\\", "/")
    exp = _exp_estable(_ttl())
    sig = _firma(normalizada, exp)
    return f"{normalizada}?exp={exp}&sig={sig}"


def verificar(ruta: str, exp: str | None, sig: str | None) -> bool:
    if not ruta or exp is None or sig is None:
        return False
    normalizada = ruta.replace("\\", "/")
    try:
        exp_num = int(exp)
    except (TypeError, ValueError):
        return False
    if exp_num <= time.time():
        return False
    esperado = _firma(normalizada, exp_num)
    try:
        return hmac.compare_digest(esperado, sig)
    except (TypeError, ValueError):
        return False


def _secreto() -> str:
    return str(current_app.config.get("UPLOAD_SIGN_SECRET") or "")


def _ttl() -> int:
    try:
        return int(current_app.config.get("UPLOAD_SIGN_TTL_SECONDS") or 86400)
    except (TypeError, ValueError):
        return 86400


def _exp_estable(ttl: int) -> int:

    ahora = int(time.time())
    return ((ahora + ttl) // _VENTANA_SEGUNDOS) * _VENTANA_SEGUNDOS


def _firma(ruta_normalizada: str, exp: int) -> str:
    mensaje = f"{ruta_normalizada}|{exp}".encode()
    return hmac.new(_secreto().encode(), mensaje, hashlib.sha256).hexdigest()
