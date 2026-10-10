from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from app.domain.time import utcnow

# Umbral global de "stock bajo" para productos sin `stock_minimo` propio. Lo usa
# la detección del cruce en `descontar_stock` y el campo `stock_bajo` del JSON.
STOCK_BAJO = 3


@dataclass
class Producto:
    nombre: str
    categoria_id: UUID
    precio: int
    stock: int = 0
    descripcion: str | None = None
    imagen: str | None = None
    activo: bool = True
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
    specs: list[str] | None = None
    descuento: int | None = None
    badge: str | None = None
    precio_original: int | None = None
    rating: int | None = None
    material: str | None = None
    tamano: str | None = None
    color: str | None = None
    # Lo marca el admin como destacado. No es lo mismo que `activo` (que es el
    # borrado logico): un producto puede estar activo y aun asi no ser un
    # lanzamiento. La seccion "Lanzamientos" de la home filtra por este flag.
    nuevo_lanzamiento: bool = False
    # URL del thumbnail para la grilla del catalogo. Es None cuando el producto
    # no tiene foto o cuando su foto ya es chica y no necesita reduccion: en
    # ese caso el consumidor debe usar `imagen`.
    imagen_thumb: str | None = None
    # Umbral propio de "stock bajo". None = usar el global `STOCK_BAJO`.
    stock_minimo: int | None = None
    # Se marca al cruzar hacia abajo el umbral en `descontar_stock` y se limpia
    # al reponer stock por encima del umbral. Queda reservado para la futura
    # notificacion al dueño: sin el aviso el admin no sabe si el cruce ya se
    # disparo una vez.
    aviso_stock_enviado: bool = False


@dataclass
class ImagenProducto:
    """Imagen de un producto almacenada como BLOB (RGBA no; bytes crudos)."""
    bytes: bytes
    content_type: str


@dataclass
class FotoColorCatalogo:
    """Foto del primer color de un producto, para la tarjeta del catalogo.

    `imagen_thumb_url` es `None` cuando ese color todavia no tiene thumbnail
    generado (se hace perezoso en su primer request), y el consumidor debe usar
    `imagen_url` en ese caso.
    """

    imagen_url: str
    imagen_thumb_url: str | None = None


@dataclass
class ColorProducto:
    """Variante de color de un producto, con su propia imagen.

    Un producto puede tener N colores (por ejemplo Hyrule blanco y negro). En el
    detalle el cliente elige el color y se muestra la imagen de ese color. Si el
    producto no declara colores se usa la imagen unica de `Producto.imagen`.
    """

    producto_id: UUID
    nombre: str
    id: UUID = field(default_factory=uuid4)
    orden: int = 0
    imagen_url: str | None = None
    # URL del thumbnail del color. None si la foto ya es chica: se usa `imagen_url`.
    imagen_thumb_url: str | None = None
    creado_en: datetime = field(default_factory=utcnow)
