import io
from typing import Tuple

import filetype
from PIL import Image


ALLOWED = {"jpg", "jpeg", "png", "webp"}
SUSPICIOUS = [
    b'<?php',
    b'<?=',
    b'<script',
    b'</script',
    b'eval(',
    b'base64_decode',
    b'javascript:',
    b'vbscript:',
    b'onerror=',
    b'onload=',
    b'onclick=',
    b'onmouseover=',
    b'<iframe',
    b'<?xml',
    b'<!doctype',
    b'<!entity',
    b'%3cscript',
    b'%3Cscript',
]


class ImagenInvalida(Exception):
    pass


def validar_imagen_segura(file_storage) -> Tuple[bytes, str]:
    raw = file_storage.read()
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass

    if not raw:
        raise ImagenInvalida("La imagen está vacía o no es válida.")

    kind = filetype.guess(raw)
    if not kind or kind.extension.lower() not in ALLOWED:
        raise ImagenInvalida("Formato de imagen no permitido. Solo JPG, PNG o WebP.")

    lower = raw.lower()
    for pattern in SUSPICIOUS:
        if pattern in lower:
            raise ImagenInvalida("La imagen contiene contenido no permitido.")

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except Exception:
        raise ImagenInvalida("La imagen está corrupta o no es válida.")

    return raw, kind.extension.lower()
