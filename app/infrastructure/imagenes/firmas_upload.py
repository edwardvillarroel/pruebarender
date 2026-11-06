"""Firmas HMAC para las URLs de las imágenes de cotización.

`GET /api/uploads/<path>` servía los archivos sin control de acceso: los
nombres UUID dificultan adivinar la ruta, pero eso no es autorización. Cada
ruta relativa (`cotizaciones/<uuid>.<ext>`) se publica ahora con
`?exp=<unix>&sig=<hmac-sha256>` y `servir_uploads` exige una firma vigente
antes de enviar el archivo. El secreto y el TTL salen de la configuración de
la app (`UPLOAD_SIGN_SECRET` / `UPLOAD_SIGN_TTL_SECONDS`).
"""

from __future__ import annotations

import hashlib
import hmac
import time

from flask import current_app


def firmar(ruta: str | None) -> str | None:
    """Devuelve `ruta` con `?exp=&sig=`; `None` y URLs absolutas pasan tal cual."""
    if ruta is None:
        return None
    if ruta.startswith(("http://", "https://")):
        return ruta
    normalizada = ruta.replace("\\", "/")
    exp = int(time.time()) + _ttl()
    sig = _firma(normalizada, exp)
    return f"{normalizada}?exp={exp}&sig={sig}"


def verificar(ruta: str, exp: str | None, sig: str | None) -> bool:
    """True solo si `sig` coincide con la firma de `ruta` y `exp` sigue vigente."""
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
        # compare_digest con no-ASCII en str lanza TypeError: firma inválida.
        return False


def _secreto() -> str:
    return str(current_app.config.get("UPLOAD_SIGN_SECRET") or "")


def _ttl() -> int:
    try:
        return int(current_app.config.get("UPLOAD_SIGN_TTL_SECONDS") or 86400)
    except (TypeError, ValueError):
        return 86400


def _firma(ruta_normalizada: str, exp: int) -> str:
    mensaje = f"{ruta_normalizada}|{exp}".encode()
    return hmac.new(_secreto().encode(), mensaje, hashlib.sha256).hexdigest()
