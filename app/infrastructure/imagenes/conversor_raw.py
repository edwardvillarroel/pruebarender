
from __future__ import annotations
import io

try: 
    import rawpy
except Exception:  
    rawpy = None

try: 
    from PIL import Image
except Exception:  
    Image = None

EXTENSIONES_RAW: frozenset[str] = frozenset({
    "raw", "dng", "nef", "nrw", "arw", "srf", "sr2", "raf", "rw2", "orf",
    "pef", "srw", "mrw", "x3f", "3fr", "iiq", "kdc", "dcr", "erf", "mos",
    "cr2", "cr3",
})

TIPOS_IMAGEN_RENDERIZABLES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
    "image/bmp",
    "image/svg+xml",
})

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


LADO_MAXIMO_ORIGINAL = 1600
CALIDAD_JPEG_OPTIMIZADO = 85
TAMANIO_MAXIMO_INTACTO = 2 * 1024 * 1024
_FORMATOS_CON_ALFA = ("PNG", "WEBP", "GIF")


def es_raw(nombre_archivo: str) -> bool:

    if not nombre_archivo or "." not in nombre_archivo:
        return False
    extension = nombre_archivo.rsplit(".", 1)[-1].strip().lower()
    return bool(extension) and extension in EXTENSIONES_RAW


def convertir_raw_a_jpeg(datos: bytes) -> bytes:

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
        with Image.fromarray(arreglo) as imagen:
            salida = io.BytesIO()
            imagen.save(salida, format="JPEG", quality=90, optimize=True)
    except Exception as exc:
        raise ValueError(_MENSAJE_CONVERSION) from exc
    return salida.getvalue()


def _tipo_mime_normalizado(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _convertir_a_rgb(imagen: "Image.Image") -> "Image.Image":


    if imagen.mode in ("RGB", "L"):
        return imagen
    if _tiene_transparencia(imagen):
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        con_alfa = imagen.convert("RGBA")
        fondo.paste(con_alfa, mask=con_alfa.split()[-1])
        return fondo
    return imagen.convert("RGB")


def _tiene_transparencia(imagen: "Image.Image") -> bool:

    if imagen.mode in ("RGBA", "LA"):
        return True
    if imagen.mode == "P":
        return "transparency" in imagen.info
    return False


def _formato_de_salida(imagen: "Image.Image", formato_actual: str) -> str:

    if _tiene_transparencia(imagen):
        return formato_actual if formato_actual in _FORMATOS_CON_ALFA else "PNG"
    return "JPEG"


def _guardar(imagen: "Image.Image", formato: str) -> bytes:
    salida = io.BytesIO()
    if formato == "JPEG":
        _convertir_a_rgb(imagen).save(
            salida, format=formato, quality=CALIDAD_JPEG_OPTIMIZADO, optimize=True
        )
    elif formato == "WEBP":
        imagen.save(salida, format=formato, quality=CALIDAD_JPEG_OPTIMIZADO)
    else:
        imagen.save(salida, format=formato, optimize=True)
    return salida.getvalue()


def optimizar_imagen(datos: bytes, content_type: str) -> tuple[bytes, str]:


    if Image is None or not datos:
        return datos, content_type

    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            imagen.load()
            if getattr(imagen, "is_animated", False):
                return datos, content_type

            if (
                max(imagen.size) <= LADO_MAXIMO_ORIGINAL
                and len(datos) <= TAMANIO_MAXIMO_INTACTO
            ):
                return datos, content_type

            if max(imagen.size) > LADO_MAXIMO_ORIGINAL:
                imagen.thumbnail(
                    (LADO_MAXIMO_ORIGINAL, LADO_MAXIMO_ORIGINAL), Image.LANCZOS
                )

            formato = _formato_de_salida(imagen, (imagen.format or "").upper())
            bytes_nuevos = _guardar(imagen, formato)
            if len(bytes_nuevos) >= len(datos):
                return datos, content_type
            return bytes_nuevos, _MIME_POR_FORMATO_PIL[formato]
    except Exception:
        return datos, content_type


def _detectar_mime_decodificable(datos: bytes) -> str | None:

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


    if es_raw(nombre_archivo):
        return optimizar_imagen(convertir_raw_a_jpeg(datos), "image/jpeg")

    if _tipo_mime_normalizado(content_type) in TIPOS_IMAGEN_RENDERIZABLES:
        return optimizar_imagen(datos, content_type)
    try:
        return optimizar_imagen(convertir_raw_a_jpeg(datos), "image/jpeg")
    except ValueError:
        pass

    mime = _detectar_mime_decodificable(datos)
    if mime is not None:
        return optimizar_imagen(datos, mime)

    raise ValueError(_MENSAJE_FORMATO)
