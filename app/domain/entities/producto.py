from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


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
    creado_en: datetime = field(default_factory=datetime.utcnow)
    specs: list[str] | None = None
    descuento: int | None = None
    badge: str | None = None
    precio_original: int | None = None
    rating: int | None = None
    material: str | None = None
    tamano: str | None = None
    color: str | None = None


@dataclass
class ImagenProducto:
    """Imagen de un producto almacenada como BLOB (RGBA no; bytes crudos)."""
    bytes: bytes
    content_type: str
