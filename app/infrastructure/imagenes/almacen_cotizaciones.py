"""Escritura de las imágenes de cotización: disco local y Supabase Storage.

`guardar_imagen_cotizacion` (F1/base) escribe en `uploads/cotizaciones/`.
`guardar_imagen_cotizacion_supabase` (F4) sube al bucket cuando la config de
Supabase está completa y DEGRADA a escritura local ante cualquier falla, con
el mismo contrato: devuelve `cotizaciones/<uuid><ext>`, la ruta relativa que
guarda `solicitudes_diseno.imagen` (formato fijo: no cambia).

Ambas escriben también la miniatura de la imagen en el momento de la subida.
Es el único punto donde los bytes ya están en memoria y ya se decodificaron
para validarlos: generarla acá evita que la primera visita al listado dispare
una descarga completa del original por cada foto. Si la miniatura no se puede
generar o guardar, no pasa nada: el serving la genera de forma perezosa.
"""

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
    """Mismo contrato que `guardar_imagen_cotizacion`, con Supabase Storage.

    - Supabase NO configurado (URL/clave/cubeta vacías): idéntico a siempre,
      escribe en disco local.
    - Configurado: sube el bytes al bucket bajo la ruta relativa y la devuelve;
      NO escribe en disco.
    - Cualquier falla de la nube (red, permisos, bucket caído): `warning` y
      fallback a disco con el MISMO nombre, para que una cotización nunca falle
      por Supabase y, si la subida quedó a medias, disco y bucket apunten al
      mismo archivo.
    """
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


# Solo se intenta la miniatura para formatos que Pillow sabe leer. Los modelos
# 3D (`.glb`) comparten los mismos escritores de almacenamiento pero no tienen
# miniatura posible.
_EXTENSIONES_IMAGEN = frozenset(
    {".png", ".jpg", ".jpeg", ".jpe", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
)


def _es_imagen(ruta: str) -> bool:
    return Path(ruta).suffix.lower() in _EXTENSIONES_IMAGEN


def _escribir_miniatura_local(contenido: bytes, ruta: str, carpeta_base) -> None:
    """Escribe la miniatura junto al original; best-effort, nunca lanza."""
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
        # Disco efímero, permisos o path raro: la via perezosa la regenera.
        logger.warning(
            "[cotizaciones] no se pudo escribir la miniatura de %s", ruta
        )


def _subir_miniatura(almacen, contenido: bytes, ruta: str) -> None:
    """Sube la miniatura al bucket; best-effort, nunca lanza."""
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
    # Si falla, `subir` ya avisa y devuelve `False`: el serving la regenera.
    almacen.subir(destino, miniatura, MIME_MINIATURA)
