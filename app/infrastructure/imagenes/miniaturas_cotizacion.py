



from __future__ import annotations

from app.infrastructure.imagenes.thumbnail import generar_thumbnail

PREFIJO_MINIATURAS = "miniaturas/cotizaciones/"

LADO_MAXIMO_MINIATURA = 400

MIME_MINIATURA = "image/jpeg"


def ruta_miniatura(ruta: str | None) -> str | None:

    if not ruta or not isinstance(ruta, str):
        return None
    normalizada = ruta.replace("\\", "/")
    if normalizada.startswith(("http://", "https://", "/")):
        return None
    partes = normalizada.split("/")
    if len(partes) != 2 or partes[0] != "cotizaciones":
        return None
    tallo = partes[1].rsplit(".", 1)[0]
    if not tallo or ".." in tallo:
        return None
    return f"{PREFIJO_MINIATURAS}{tallo}.jpg"


def crear_miniatura(datos: bytes | None) -> bytes | None:

    if not datos:
        return None
    generado = generar_thumbnail(
        datos, MIME_MINIATURA, lado_maximo=LADO_MAXIMO_MINIATURA
    )
    return generado[0] if generado else None
