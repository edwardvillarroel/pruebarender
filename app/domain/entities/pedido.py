from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.enums import EstadoPedido


@dataclass
class Pedido:
    usuario_id: UUID
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    total: int = 0
    direccion_envio: str | None = None
    codigo_seguimiento: str | None = None
    estado_seguimiento: str | None = None
    seguimiento_actualizado_en: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=datetime.utcnow)
    detalles: list[DetallePedido] = field(default_factory=list)