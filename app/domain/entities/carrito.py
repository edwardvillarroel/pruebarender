from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from app.domain.time import utcnow


@dataclass
class ItemCarrito:


    producto_id: str
    cantidad: int
    color: str | None = None
    imagen: str | None = None
    id: UUID = field(default_factory=uuid4)
    agregado_en: datetime = field(default_factory=utcnow)


@dataclass
class Carrito:


    usuario_id: str
    items: list[ItemCarrito] = field(default_factory=list)
    actualizado_en: datetime = field(default_factory=utcnow)
