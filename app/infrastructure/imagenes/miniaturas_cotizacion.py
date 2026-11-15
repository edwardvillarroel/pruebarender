"""Miniaturas de las imágenes de cotización.

Las fotos de referencia se guardan a resolución completa (hasta 10 MB), pero el
listado las muestra en una caja de 96×96: bajar el original entero para pintar
eso es lo que hacía que las cotizaciones tardaran en cargar.

La miniatura se genera de forma perezosa y se guarda donde vive el original
(bucket de Supabase o disco local), así las peticiones siguientes ya no tocan el
archivo grande. Es el mismo patrón que el thumbnail del catálogo
(`app/infrastructure/imagenes/thumbnail.py`): no hay script de backfill.

`crear_miniatura` devuelve `None` cuando no hay nada que ganar (la foto ya es
chica) o cuando Pillow no puede decodificarla. `None` no es un error: el
llamador debe servir el original, nunca dejar la miniatura rota.
"""

from __future__ import annotations

from app.infrastructure.imagenes.thumbnail import generar_thumbnail

# Prefijo propio dentro del bucket/disco: `cotizaciones/` es la carpeta que
# lista la purga buscando huérfanos, y las miniaturas no son huérfanas (su
# original manda). Mantenerlas aparte evita que la purga las confunda.
PREFIJO_MINIATURAS = "miniaturas/cotizaciones/"

# La caja donde se muestran mide 96px. En una pantalla retina eso son ~192px
# reales; 400px cubre cualquier densidad sin acercarse al peso del original.
LADO_MAXIMO_MINIATURA = 400

# Pillow escribe JPEG en `crear_miniatura`; el MIME acompaña esa decisión.
MIME_MINIATURA = "image/jpeg"


def ruta_miniatura(ruta: str | None) -> str | None:
    """Ruta de la miniatura de una imagen de cotización, o `None` si no aplica.

    Solo entiende el formato que escribe la app (`cotizaciones/<uuid>.<ext>`).
    URLs absolutas, rutas absolutas, carpetas ajenas y rutas con `..` quedan sin
    miniatura: el llamador sirve el original tal cual.
    """
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
    """JPEG reducido de `datos`, o `None` si no conviene/no se puede.

    `None` es una respuesta válida: la foto ya es chica, Pillow no está
    instalado o el archivo no se puede decodificar.
    """
    if not datos:
        return None
    generado = generar_thumbnail(
        datos, MIME_MINIATURA, lado_maximo=LADO_MAXIMO_MINIATURA
    )
    return generado[0] if generado else None
