"""Generación de thumbnails para las fotos de producto y de color.

Las fotos originales se guardan tal cual (el detalle del producto las necesita
en resolución completa), pero el catálogo mostraba cada una en una tarjeta de
~240px descargando el archivo entero: 43 MB para 18 productos, 2,4 MB en
promedio. El thumbnail reduce eso a decenas de KB sin tocar el original.

La generación es perezosa: no hay script de backfill. Si el thumbnail no existe
cuando se pide, se genera desde la imagen original, se guarda y se sirve; las
peticiones siguientes ya leen el BLOB. Cuando se reemplaza la foto original, el
thumbnail se invalida y se regenera en el próximo request.

Este módulo es la única pieza de infraestructura que conoce Pillow para esto.
`generar_thumbnail` es una función libre: la recibe el caso de uso por
constructor, en el punto de composición, como
`GestionarProducto(ProductoRepository(), generador_thumb=generar_thumbnail)`
(ver `app/__init__.py`). La capa API nunca la importa ni la lee de
`app.config`; usa el servicio ya armado. Por eso este módulo no importa Flask
ni SQLAlchemy y se puede probar sin levantar la app.
"""

from __future__ import annotations

import io

try:  # dependencia opcional: no debe romper el arranque de la app
    from PIL import Image
except Exception:  # pragma: no cover - dependencia opcional ausente
    Image = None

# Lado mayor del thumbnail en px. La tarjeta del catálogo mide ~240px y con
# `minmax(240px, 1fr)` puede llegar a ~400px; 600px cubre pantallas retina sin
# que el archivo se dispare.
LADO_MAXIMO = 600

# JPEG quality 82: apenas diferencia visual frente a la original para fotos de
# producto, y~5-10x menos bytes que un PNG equivalente.
CALIDAD_JPEG = 82

# Por debajo de este tamaño el original ya es más chico que el thumbnail que
# generariamos: conviene devolverlo tal cual antes que recomprimirlo.
TAMANIO_MINIMO_BYTES = 16 * 1024


def _convertir_a_rgb(imagen: "Image.Image") -> "Image.Image":
    """Deja la imagen en un modo que JPEG pueda guardar.

    PNG con canal alfa (RGBA) o paletizado (P) no se pueden escribir como JPEG;
    sin esto `save()` falla con `OSError: cannot write mode RGBA as JPEG`.
    Las fotos de producto van sobre fondo blanco, así que se compone sobre
    blanco en vez de descartar el canal alfa.
    """
    if imagen.mode in ("RGB", "L"):
        return imagen
    if imagen.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        if imagen.mode != "P":
            imagen = imagen.convert("RGBA")
        fondo.paste(imagen, mask=imagen.split()[-1])
        return fondo
    return imagen.convert("RGB")


def generar_thumbnail(
    datos: bytes,
    content_type: str,
) -> tuple[bytes, str] | None:
    """Devuelve `(bytes, content_type)` del thumbnail, o `None` si no se puede.

    `None` no es un error: el llamador debe seguir sirviendo la imagen original.
    No falla si Pillow no está instalado, el archivo está dañado o el
    formato no se puede decodificar.
    """
    if Image is None or not datos:
        return None

    # Ya es chico: recomprimirlo solo perderia calidad sin ahorrar nada.
    if len(datos) <= TAMANIO_MINIMO_BYTES:
        return None

    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            imagen.load()
            if max(imagen.size) <= LADO_MAXIMO:
                return None
            imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
            salida = io.BytesIO()
            _convertir_a_rgb(imagen).save(
                salida, format="JPEG", quality=CALIDAD_JPEG, optimize=True
            )
            return salida.getvalue(), "image/jpeg"
    except Exception:
        # Una foto que Pillow no puede leer no debe tumbar el catalogo: se
        # devuelve None y el llamador sirve la original.
        return None
