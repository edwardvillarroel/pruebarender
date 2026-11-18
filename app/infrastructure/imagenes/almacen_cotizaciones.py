


from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)


def guardar_imagen_cotizacion(contenido: bytes, extension: str, carpeta_base) -> str:
    carpeta = Path(carpeta_base) / "cotizaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = _nombre_archivo(extension)
    _escribir_local(carpeta, nombre, contenido)
    ruta = f"cotizaciones/{nombre}"
    _escribir_miniatura_local(contenido, ruta, carpeta_base)
    return ruta


def guardar_imagen_cotizacion_supabase(
    contenido: bytes, extension: str, carpeta_base
) -> str:

    from app.infrastructure.storage.supabase_storage import (
        almacen_desde_config,
        tipo_mime,
    )

    almacen = almacen_desde_config()
    if almacen is None:
        return guardar_imagen_cotizacion(contenido, extension, carpeta_base)

    ext = _extension_punto(extension)
    nombre = f"{uuid4().hex}{ext}"
    ruta = f"cotizaciones/{nombre}"
    if almacen.subir(ruta, contenido, tipo_mime(ext)):
        _subir_miniatura(almacen, contenido, ruta)
        return ruta

    logger.warning(
        "[cotizaciones] Supabase Storage no aceptó %s; se guarda en disco local",
        ruta,
    )
    carpeta = Path(carpeta_base) / "cotizaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    _escribir_local(carpeta, nombre, contenido)
    _escribir_miniatura_local(contenido, ruta, carpeta_base)
    return ruta


def _extension_punto(extension: str) -> str:
    return extension if extension.startswith(".") else f".{extension}"


def _nombre_archivo(extension: str) -> str:
    return f"{uuid4().hex}{_extension_punto(extension)}"


def _escribir_local(carpeta: Path, nombre: str, contenido: bytes) -> None:
    with open(carpeta / nombre, "wb") as f:
        f.write(contenido)


_EXTENSIONES_IMAGEN = frozenset(
    {".png", ".jpg", ".jpeg", ".jpe", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
)


def _es_imagen(ruta: str) -> bool:
    return Path(ruta).suffix.lower() in _EXTENSIONES_IMAGEN


def _escribir_miniatura_local(contenido: bytes, ruta: str, carpeta_base) -> None:
    if not _es_imagen(ruta):
        return
    from app.infrastructure.imagenes.miniaturas_cotizacion import (
        crear_miniatura,
        ruta_miniatura,
    )

    destino = ruta_miniatura(ruta)
    if destino is None:
        return
    miniatura = crear_miniatura(contenido)
    if miniatura is None:
        return
    archivo = Path(carpeta_base) / destino
    try:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(miniatura)
    except OSError:
        logger.warning(
            "[cotizaciones] no se pudo escribir la miniatura de %s", ruta
        )


def _subir_miniatura(almacen, contenido: bytes, ruta: str) -> None:
    if not _es_imagen(ruta):
        return
    from app.infrastructure.imagenes.miniaturas_cotizacion import (
        MIME_MINIATURA,
        crear_miniatura,
        ruta_miniatura,
    )

    destino = ruta_miniatura(ruta)
    if destino is None:
        return
    miniatura = crear_miniatura(contenido)
    if miniatura is None:
        return
    almacen.subir(destino, miniatura, MIME_MINIATURA)
