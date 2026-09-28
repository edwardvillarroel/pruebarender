"""Conversión de fotos RAW de cámara a JPEG para almacenarlas como BLOB.

Los navegadores no saben decodificar los formatos RAW de cámara (CR2, NEF,
DNG, ...), así que el backend los transforma a JPEG antes de guardarlos y
servirlos; de lo contrario el tag `<img>` mostraría la imagen en blanco y el
tipo MIME guardado haría que el navegador se negara a renderizarla.

Este módulo es la única pieza de infraestructura que conoce `rawpy`/Pillow
para el catálogo: la capa API nunca lo importa, recibe el conversor
inyectado via `current_app.config["CONVERSOR_IMAGEN"]` (ver `app/__init__.py`).

Además de convertir, `normalizar_imagen` OPTIMIZA: las fotos de camara pesan
2-4 MB y llegan con miles de píxeles de lado, y la web solo muestra tarjetas de
~240px y fotos ampliadas de ~800px. `optimizar_imagen` las deja en 1600px como
máximo y en JPEG quality 85, respetando el canal alfa de los PNG/WEBP.
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

# Lado mayor (px) con el que se guarda la foto de producto. Por encima de esto
# no hay nada que ver: la tarjeta del catalogo mide ~240px y la foto ampliada del
# detalle ~800px, asi que 1600px sigue cubriendo pantallas retina. Las fotos
# de camara (6000x4000) bajan de 3-5 MB a unos 400 KB.
LADO_MAXIMO_ORIGINAL = 1600

# JPEG quality 85: diferencia invisible frente a la original en fotos de
# producto y pesa ~5x menos que el JPEG de camara (q90 + metadatos EXIF).
CALIDAD_JPEG_OPTIMIZADO = 85

# Techo de bytes para dar la foto por "ya optimizada" si además cabe en el lado
# maximo. 2 MB es el techo de la columna BLOB de los productos en la practica:
# lo que pesa mas es una foto sin comprimir o un PNG sin alfa, que se
# recomprimen aunque entren en 1600px.
TAMANIO_MAXIMO_INTACTO = 2 * 1024 * 1024

# Formatos que conservan el canal alfa y por lo tanto no se fuerzan a JPEG:
# convertirlos taparia la transparencia de logos y disenos.
_FORMATOS_CON_ALFA = ("PNG", "WEBP", "GIF")


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
        with Image.fromarray(arreglo) as imagen:
            salida = io.BytesIO()
            imagen.save(salida, format="JPEG", quality=90, optimize=True)
    except Exception as exc:
        raise ValueError(_MENSAJE_CONVERSION) from exc
    return salida.getvalue()


def _tipo_mime_normalizado(content_type: str | None) -> str:
    """Tipo MIME en minusculas y sin parametros (`; charset=...`)."""
    return (content_type or "").split(";", 1)[0].strip().lower()


def _convertir_a_rgb(imagen: "Image.Image") -> "Image.Image":
    """Deja la imagen en un modo que JPEG pueda guardar.

    Copia de la version que vive en `thumbnail.py`: el modulo de thumbnails es
    el unico que conoce Pillow para el catalogo y este tambien, y duplicar
    treinta lineas es preferible a atarlos (uno depende del otro y cualquier
    cambio en uno rompe al otro).

    La diferencia con la original: aqui solo se compone sobre blanco si la
    imagen TIENE canal alfa. Un PNG paletizado sin alfa tiene una sola banda, y
    usarla como mascara hace fallar `paste` con `bad transparency mask`; esos se
    convierten a RGB directo, que es lo que corresponde.
    """
    if imagen.mode in ("RGB", "L"):
        return imagen
    if _tiene_transparencia(imagen):
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        con_alfa = imagen.convert("RGBA")
        fondo.paste(con_alfa, mask=con_alfa.split()[-1])
        return fondo
    return imagen.convert("RGB")


def _tiene_transparencia(imagen: "Image.Image") -> bool:
    """Indica si la imagen tiene canal alfa con algo transparente detras.

    Un PNG en modo `P` no siempre tiene alfa: la clave `transparency` en
    `info` es la que lo dice, y sin ella hay que tratarlo como opaco.
    """
    if imagen.mode in ("RGBA", "LA"):
        return True
    if imagen.mode == "P":
        return "transparency" in imagen.info
    return False


def _formato_de_salida(imagen: "Image.Image", formato_actual: str) -> str:
    """Elige el formato con el que se guarda la foto ya optimizada.

    Con transparencia se respeta el formato de entrada (PNG/WEBP/GIF) porque al
    pasar a JPEG el canal alfa se pierde y los logos salen con fondo negro. Sin
    transparencia, todo a JPEG quality 85: es el formato que pesa menos y el que
    el navegador siempre sabe dibujar.
    """
    if _tiene_transparencia(imagen):
        return formato_actual if formato_actual in _FORMATOS_CON_ALFA else "PNG"
    return "JPEG"


def _guardar(imagen: "Image.Image", formato: str) -> bytes:
    """Serializa la imagen al formato pedido y devuelve los bytes."""
    salida = io.BytesIO()
    if formato == "JPEG":
        _convertir_a_rgb(imagen).save(
            salida, format=formato, quality=CALIDAD_JPEG_OPTIMIZADO, optimize=True
        )
    elif formato == "WEBP":
        # WEBP no entiende `optimize`: su own knob es `quality`.
        imagen.save(salida, format=formato, quality=CALIDAD_JPEG_OPTIMIZADO)
    else:
        imagen.save(salida, format=formato, optimize=True)
    return salida.getvalue()


def optimizar_imagen(datos: bytes, content_type: str) -> tuple[bytes, str]:
    """Reescala y recomprime una foto de producto para lo que se sirve en la web.

    Las fotos se suben tal cual las saca la camara o el celular: 2-4 MB por
    producto, con el lado mayor en miles de pixeles. Eso no aporta nada para una
    tarjeta de catalogo ni para la foto ampliada del detalle, y se descarga en
    cada peticion. Aqui se dejan en 1600px como maximo y en JPEG quality 85.

    El archivo se devuelve intacto cuando ya cabe en el presupuesto (lado maximo
    y `TAMANIO_MAXIMO_INTACTO`), y tambien cuando reprocesarlo lo haria MAS
    grande: optimizar nunca puede hacer crecer el archivo. Salen intactos
    ademas los formatos que Pillow no puede volver a codificar sin perder algo
    (GIF animado) y, si Pillow no esta instalado, todos: es una dependencia
    opcional y sin ella la imagen se guarda tal como se subio, que es como
    funcionaba antes de este modulo.
    """
    if Image is None or not datos:
        return datos, content_type

    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            imagen.load()
            # Una animacion (GIF) perderia todos los cuadros menos el primero si
            # se reescala y se guarda como imagen simple.
            if getattr(imagen, "is_animated", False):
                return datos, content_type

            if (
                max(imagen.size) <= LADO_MAXIMO_ORIGINAL
                and len(datos) <= TAMANIO_MAXIMO_INTACTO
            ):
                return datos, content_type

            if max(imagen.size) > LADO_MAXIMO_ORIGINAL:
                # `thumbnail` conserva la proporcion y no agranda una imagen que
                # ya es mas chica que el lado maximo.
                imagen.thumbnail(
                    (LADO_MAXIMO_ORIGINAL, LADO_MAXIMO_ORIGINAL), Image.LANCZOS
                )

            formato = _formato_de_salida(imagen, (imagen.format or "").upper())
            bytes_nuevos = _guardar(imagen, formato)
            if len(bytes_nuevos) >= len(datos):
                # Reprocesar puede PESAR MAS que el archivo original: un PNG de
                # logo muy comprensible que al reescalar queda en 1600px y se
                # guarda como JPEG puede pasar de 40 KB a 100 KB. Optimizar
                # para que el archivo crezca seria traicionar el objetivo, asi
                # que en ese caso se deja el original como estaba.
                return datos, content_type
            return bytes_nuevos, _MIME_POR_FORMATO_PIL[formato]
    except Exception:
        # Optimizar es una mejora, no un requisito: una foto que Pillow no sabe
        # decodificar se guarda como se subio en vez de rechazar el alta.
        return datos, content_type


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

    - RAW de camara (por extension): se convierte a JPEG y despues se optimiza.
      Si la conversion falla (formato no soportado, archivo danado o
      dependencias ausentes) lanza `ValueError` con mensaje en español.
    - Imagen ya navegable (JPG/PNG/WEBP/...): se optimiza y se devuelve.
    - Ni RAW ni imagen decodificable: `ValueError` con mensaje en español
      que nombra los formatos soportados.

    Toda salida pasa por `optimizar_imagen`, que deja la foto en 1600px y JPEG
    quality 85 (respetando el canal alfa) antes de guardarla. Un archivo que ya
    entra en el presupuesto sale intacto, y sin Pillow sale tal cual subio: la
    optimizacion no puede romper un alta que antes funcionaba.
    """
    if es_raw(nombre_archivo):
        return optimizar_imagen(convertir_raw_a_jpeg(datos), "image/jpeg")

    if _tipo_mime_normalizado(content_type) in TIPOS_IMAGEN_RENDERIZABLES:
        return optimizar_imagen(datos, content_type)

    # Tipo no navegable y sin extension RAW: puede ser un RAW con extension
    # rara o una imagen valida con content_type mal declarado.
    try:
        return optimizar_imagen(convertir_raw_a_jpeg(datos), "image/jpeg")
    except ValueError:
        pass

    mime = _detectar_mime_decodificable(datos)
    if mime is not None:
        return optimizar_imagen(datos, mime)

    raise ValueError(_MENSAJE_FORMATO)
