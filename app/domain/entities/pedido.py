from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.enums import EstadoPedido
from app.domain.time import utcnow


@dataclass
class Pedido:
    usuario_id: UUID
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    total: int = 0
    direccion_envio: str | None = None
    entrega: str = "retiro"
    codigo_seguimiento: str | None = None
    transportista: str | None = None
    estado_seguimiento: str | None = None
    seguimiento_actualizado_en: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
    detalles: list[DetallePedido] = field(default_factory=list)
    # 1 si el pedido esta `entregado` y tiene al menos un producto sin resena
    # del usuario; 0 en el resto. Derivado (no es columna de la tabla): lo
    # calcula `PedidoRepository.list_by_usuario` con una subquery.
    resenas_pendientes: int = 0
