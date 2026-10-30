from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class DetallePedido:
    pedido_id: UUID
    producto_id: UUID | None
    cantidad: int
    precio_unitario: int
    color: str | None = None
    nombre: str | None = None
    imagen: str | None = None
    id: UUID = field(default_factory=uuid4)
    precio_original: int | None = None