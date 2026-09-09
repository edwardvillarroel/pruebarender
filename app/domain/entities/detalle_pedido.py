from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class DetallePedido:
    pedido_id: UUID
    producto_id: UUID
    cantidad: int
    precio_unitario: int
    id: UUID = field(default_factory=uuid4)