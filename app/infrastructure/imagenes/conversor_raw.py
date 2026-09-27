"""Conversión de fotos RAW de cámara a JPEG para almacenarlas como BLOB.

Los navegadores no saben decodificar los formatos RAW de cámara (CR2, NEF,
DNG, ...), así que el backend los transforma a JPEG antes de guardarlos y
servirlos; de lo contrario el tag `<img>` mostraría la imagen en blanco y el
tipo MIME guardado haría que el navegador se negara a renderizarla.

Este módulo es la única pieza de infraestructura que conoce `rawpy`/Pillow
para el catálogo: la capa API nunca lo importa, recibe el conversor
inyectado via `current_app.config["CONVERSOR_IMAGEN"]` (ver `app/__init__.py`).
"""

from __future__ import annotations

import io

try:  # dependencia opcional: no debe romper el arranque de la app
    import rawpy
except Exception:  # pragma: no cover - dependencia opcional ausente
    rawpy = None

try:  # dependencia opcional: no debe romper el arranque de la app
    from PIL import Image
except Exception:  # pragma: no cover - dependencia opcional ausente
    Image = None

# Extensiones de archivo RAW de cámara (minúsculas, sin punto).
EXTENSIONES_RAW: frozenset[str] = frozenset({
    "raw", "dng", "nef", "nrw", "arw", "srf", "sr2", "raf", "rw2", "orf",
    "pef", "srw", "mrw", "x3f", "3fr", "iiq", "kdc", "dcr", "erf", "mos",
    "cr2", "cr3",
})

# Tipos MIME de imagen que el navegador dibuja directamente en un <img>.
TIPOS_IMAGEN_RENDERIZABLES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
    "image/bmp",
    "image/svg+xml",
})

# Formato PIL -> tipo MIME navegable (para content_type mal declarado).
_MIME_POR_FORMATO_PIL = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
    "AVIF": "image/avif",
}

_MENSAJE_DEPENDENCIAS = (
    "No se pudo convertir la foto RAW a JPEG: el modulo de conversion "
    "(rawpy/Pillow) no esta disponible en el servidor."
)
_MENSAJE_CONVERSION = (
    "No se pudo convertir la foto RAW a JPEG: el formato no es compatible "
    "con la camara o el archivo esta danado."
)
_MENSAJE_FORMATO = (
    "Formato de imagen no soportado. Usa JPG, PNG, WEBP, GIF, AVIF, BMP o "
    "SVG, o una foto RAW de camara (CR2, NEF, DNG, ARW, RAF, RW2, ORF...)."
)


def es_raw(nombre_archivo: str) -> bool:
    """Detecta si el nombre de archivo tiene extension de RAW de camara.

    Tolera mayusculas/minusculas y devuelve `False` si el nombre esta vacio
    o no tiene extension.
    """
    if not nombre_archivo or "." not in nombre_archivo:
        return False
    extension = nombre_archivo.rsplit(".", 1)[-1].strip().lower()
    return bool(extension) and extension in EXTENSIONES_RAW


def convertir_raw_a_jpeg(datos: bytes) -> bytes:
    """Decodifica bytes RAW de camara y los devuelve como JPEG (calidad 90).

    Cierra siempre el manejador de libraw para no filtrar descriptores de
    archivo. Lanza `ValueError` con mensaje en español si las dependencias
    opcionales faltan o el archivo RAW no se puede procesar.
    """
    if rawpy is None or Image is None:
        raise ValueError(_MENSAJE_DEPENDENCIAS)
    try:
        manejador = rawpy.imread(io.BytesIO(datos))
    except Exception as exc:
        raise ValueError(_MENSAJE_CONVERSION) from exc
    try:
        arreglo = manejador.postprocess()
    except Exception as exc:
        raise ValueError(_MENSAJE_CONVERSION) from exc
    finally:
        manejador.close()
    try:
        imagen = Image.fromarray(arreglo)
        salida = io.BytesIO()
        imagen.save(salida, format="JPEG", quality=90, optimize=True)
    except Exception as exc:
        raise ValueError(_MENSAJE_CONVERSION) from exc
    return salida.getvalue()


def _tipo_mime_normalizado(content_type: str | None) -> str:
    """Tipo MIME en minusculas y sin parametros (`; charset=...`)."""
    return (content_type or "").split(";", 1)[0].strip().lower()


def _detectar_mime_decodificable(datos: bytes) -> str | None:
    """Devuelve el tipo MIME si Pillow sabe decodificar los bytes, o `None`.

    Se usa cuando el archivo no tiene extension RAW pero el `content_type`
    no es navegable (por ejemplo `application/octet-stream`): si los bytes
    son una imagen valida, se conservan y solo se corrige el tipo MIME.
    """
    if Image is None:
        return None
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            formato = (imagen.format or "").upper()
    except Exception:
        return None
    return _MIME_POR_FORMATO_PIL.get(formato)


def normalizar_imagen(
    datos: bytes,
    content_type: str,
    nombre_archivo: str,
) -> tuple[bytes, str]:
    """Normaliza una imagen subida para que el navegador pueda mostrarla.

    - RAW de camara (por extension): se convierte a JPEG. Si la conversion
      falla (formato no soportado, archivo danado o dependencias ausentes)
      lanza `ValueError` con mensaje en español.
    - Imagen ya navegable (JPG/PNG/WEBP/...): se devuelve intacta.
    - Ni RAW ni imagen decodificable: `ValueError` con mensaje en español
      que nombra los formatos soportados.
    """
    if es_raw(nombre_archivo):
        return convertir_raw_a_jpeg(datos), "image/jpeg"

    if _tipo_mime_normalizado(content_type) in TIPOS_IMAGEN_RENDERIZABLES:
        return datos, content_type

    # Tipo no navegable y sin extension RAW: puede ser un RAW con extension
    # rara o una imagen valida con content_type mal declarado.
    try:
        return convertir_raw_a_jpeg(datos), "image/jpeg"
    except ValueError:
        pass

    mime = _detectar_mime_decodificable(datos)
    if mime is not None:
        return datos, mime

    raise ValueError(_MENSAJE_FORMATO)
