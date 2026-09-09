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