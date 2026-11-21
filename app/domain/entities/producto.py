from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from app.domain.time import utcnow

STOCK_BAJO = 3


@dataclass
class Producto:
    nombre: str
    categoria_id: UUID
    precio: int
    stock: int = 0
    descripcion: str | None = None
    imagen: str | None = None
    imagen_url: str | None = None
    activo: bool = True
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
    specs: list[str] | None = None
    descuento: int | None = None
    badge: str | None = None
    precio_original: int | None = None
    rating: float | None = None
    resenas_count: int = 0
    material: str | None = None
    tamano: str | None = None
    color: str | None = None
    nuevo_lanzamiento: bool = False
    imagen_thumb: str | None = None
    stock_minimo: int | None = None
    aviso_stock_enviado: bool = False
    aviso_stock_notificado_en: datetime | None = None


@dataclass
class ProductoVendido:


    producto: Producto
    unidades: int
    ingresos: int


@dataclass
class ImagenProducto:
    bytes: bytes
    content_type: str


@dataclass
class FotoColorCatalogo:


    imagen_url: str
    imagen_thumb_url: str | None = None


@dataclass
class ColorProducto:


    producto_id: UUID
    nombre: str
    id: UUID = field(default_factory=uuid4)
    orden: int = 0
    imagen_url: str | None = None
    imagen_thumb_url: str | None = None
    creado_en: datetime = field(default_factory=utcnow)
